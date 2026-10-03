import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (r.raw ?? JSON.stringify(r.body ?? {})) }; };
async function connect(spec, handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(spec);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/kayzen.json", import.meta.url), "utf8"));
const BASIC = Buffer.from("kz-key:kz-api-secret").toString("base64");
Object.assign(process.env, { PLATFORM_MCP_KAYZEN_API_BASIC: BASIC, PLATFORM_MCP_KAYZEN_USERNAME: "ops@example.com", PLATFORM_MCP_KAYZEN_PASSWORD: "PASSWORD-kz", PLATFORM_MCP_KAYZEN_ADVERTISER_ID: "108993" });

test("kayzen password grant sends Basic header + JSON body, then bearer (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return url.pathname === "/v1/authentication/token" ? { body: { access_token: "ACCESS-kz", expires_in: "1799" } } : { body: { advertiser: { balance: "10.00" } } }; });
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, false);
  assert.equal(seen[0].init.headers.Authorization, `Basic ${BASIC}`);
  assert.deepEqual(JSON.parse(seen[0].init.body), { grant_type: "password", username: "ops@example.com", password: "PASSWORD-kz" });
  assert.equal(seen[1].init.headers.Authorization, "Bearer ACCESS-kz");
  assert.equal(seen[1].url.searchParams.get("advertiser_id"), "108993");
});

test("kayzen update_budget PATCHes data.campaign.day_budget and pause PUTs status (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return url.pathname.endsWith("/token") ? { body: { access_token: "ACCESS-kz" } } : { body: {} }; });
  const res = await client.callTool({ name: "update_budget", arguments: { campaign_id: "135858", daily_budget: 250 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "updated");
  const patch = seen.find((s) => s.init.method === "PATCH");
  assert.equal(patch.url.pathname, "/v1/campaigns/135858");
  assert.deepEqual(JSON.parse(patch.init.body), { data: { campaign: { day_budget: 250 } } });
  await client.callTool({ name: "pause_resume", arguments: { campaign_id: "135858", action: "pause" } });
  const put = seen.find((s) => s.init.method === "PUT");
  assert.equal(put.url.pathname, "/v1/campaigns/135858/status");
  assert.deepEqual(JSON.parse(put.init.body), { status: "paused" });
});

test("kayzen get_report builds the report_data body with a campaign filter (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return url.pathname.endsWith("/token") ? { body: { access_token: "ACCESS-kz" } } : { body: { data: [{ day: "2026-09-01", advertiser_spend: 3.5 }] } }; });
  const res = await client.callTool({ name: "get_report", arguments: { account_id: "108993", campaign_id: "138939", date_from: "2026-09-01", date_to: "2026-09-07" } });
  assert.equal(res.structuredContent.rows[0].spend, 3.5);
  const body = JSON.parse(seen.find((s) => s.url.pathname === "/v1/report_data").init.body);
  assert.deepEqual(body.filters, { campaign_id: [138939] });
  assert.equal(body.advertiser_id, 108993);
  assert.deepEqual(body.group_by, ["day", "campaign_id", "campaign_name"]);
});
