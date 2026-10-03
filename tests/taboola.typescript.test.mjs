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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/taboola.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_TABOOLA_CLIENT_ID: "tbcid", PLATFORM_MCP_TABOOLA_CLIENT_SECRET: "tbsecret", PLATFORM_MCP_TABOOLA_ACCOUNT_ID: "demo-advertiser" });

test("taboola update_budget: POST daily_cap under the configured account (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.pathname === "/backstage/oauth/token") return { body: { access_token: "CZ0OAAAAtoken", expires_in: 43200 } };
    return { body: { id: "5750752", daily_cap: 150 } };
  });
  const res = await client.callTool({ name: "update_budget", arguments: { campaign_id: "5750752", daily_budget: 150 } });
  assert.equal(res.isError, false);
  assert.equal(form(seen[0].init.body).grant_type, "client_credentials");
  assert.equal(seen[1].url.href, "https://backstage.taboola.com/backstage/api/1.0/demo-advertiser/campaigns/5750752");
  assert.deepEqual(JSON.parse(seen[1].init.body), { daily_cap: 150 });
  assert.equal(res.structuredContent.status, "updated");
});
