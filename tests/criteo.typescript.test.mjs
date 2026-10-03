import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (r.raw ?? JSON.stringify(r.body ?? {})) }; };
const form = (body) => Object.fromEntries(new URLSearchParams(body));
async function connect(spec, handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(spec);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/criteo.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_CRITEO_CLIENT_ID: "crit-cid", PLATFORM_MCP_CRITEO_CLIENT_SECRET: "critsecret", PLATFORM_MCP_CRITEO_CURRENCY: "EUR" });

test("criteo update_budget: client credentials in the body, PATCH with a data array (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.pathname === "/oauth2/token") return { body: { access_token: "CRT", token_type: "Bearer", expires_in: 900 } };
    return { body: { data: [{ id: "555", type: "Campaign" }], errors: [], warnings: [] } };
  });
  const res = await client.callTool({ name: "update_budget", arguments: { campaign_id: "555", daily_budget: 80 } });
  assert.equal(res.isError, false);
  assert.deepEqual(form(seen[0].init.body), { grant_type: "client_credentials", client_id: "crit-cid", client_secret: "critsecret" });
  assert.equal(seen[1].init.method, "PATCH");
  assert.equal(seen[1].url.href, "https://api.criteo.com/2026-07/marketing-solutions/campaigns");
  assert.equal(seen[1].init.headers.Authorization, "Bearer CRT");
  assert.deepEqual(JSON.parse(seen[1].init.body), { data: [{ id: "555", type: "Campaign", attributes: { spendLimit: { spendLimitAmount: { value: 80 }, spendLimitRenewal: "daily", spendLimitType: "capped" } } }] });
  assert.equal(res.structuredContent.status, "updated");
  assert.equal(res.structuredContent.campaign_id, "555");
});

test("criteo list_campaigns filters by advertiser id array (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.pathname === "/oauth2/token") return { body: { access_token: "CRT", expires_in: 900 } };
    return { body: { data: [{ id: "555", type: "Campaign", attributes: { name: "Retargeting", spendLimit: { spendLimitAmount: { value: 100 } } } }] } };
  });
  const res = await client.callTool({ name: "list_campaigns", arguments: { account_id: "13" } });
  assert.deepEqual(JSON.parse(seen[1].init.body), { filters: { advertiserIds: ["13"] } });
  assert.equal(res.structuredContent.campaigns[0].budget, 100);
});
