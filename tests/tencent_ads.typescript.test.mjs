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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/tencent_ads.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_TENCENT_ADS_CLIENT_ID: "1110001", PLATFORM_MCP_TENCENT_ADS_CLIENT_SECRET: "SECRET-tq", PLATFORM_MCP_TENCENT_ADS_REFRESH_TOKEN: "REFRESH-tq", PLATFORM_MCP_TENCENT_ADS_ACCOUNT_ID: "51959" });
const TOKEN = { code: 0, message: "", data: { access_token: "ACCESS-tq", access_token_expires_in: 86400 } };

test("tencent_ads refresh by GET, then access_token/timestamp/32-char nonce on the query (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return url.pathname === "/oauth/token" ? { body: TOKEN } : { body: { code: 0, data: { list: [{ adgroup_id: 7001, adgroup_name: "春季", configured_status: "AD_STATUS_NORMAL" }], page_info: { total_number: 1 } } } }; });
  const res = await client.callTool({ name: "list_campaigns", arguments: { account_id: "51959" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.campaigns[0].id, "7001");
  assert.equal(seen[0].init.method, "GET");
  assert.equal(seen[0].url.searchParams.get("grant_type"), "refresh_token");
  assert.equal(seen[0].url.searchParams.get("client_secret"), "SECRET-tq");
  const q = seen[1].url.searchParams;
  assert.equal(q.get("access_token"), "ACCESS-tq");
  assert.match(q.get("nonce"), /^[0-9a-f]{32}$/);
  assert.ok(Math.abs(Number(q.get("timestamp")) - Date.now() / 1000) < 60);
  assert.equal(q.get("account_id"), "51959");
});

test("tencent_ads daily report sends JSON-encoded date_range and filtering (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return url.pathname === "/oauth/token" ? { body: TOKEN } : { body: { code: 0, data: { list: [{ date: "2026-09-01", adgroup_id: 7001, cost: 12345 }] } } }; });
  const res = await client.callTool({ name: "get_report", arguments: { account_id: "51959", campaign_id: "7001", date_from: "2026-09-01", date_to: "2026-09-07" } });
  assert.equal(res.structuredContent.rows[0].cost_fen, 12345);
  const q = seen[1].url.searchParams;
  assert.deepEqual(JSON.parse(q.get("date_range")), { start_date: "2026-09-01", end_date: "2026-09-07" });
  assert.deepEqual(JSON.parse(q.get("filtering")), [{ field: "adgroup_id", operator: "EQUALS", values: ["7001"] }]);
});

test("tencent_ads update_budget converts CNY to fen and a non-zero code is an error (wire)", async () => {
  const seen = []; let n = 0;
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); if (url.pathname === "/oauth/token") return { body: TOKEN }; n += 1; return { body: n === 1 ? { code: 0, data: { adgroup_id: 7001 } } : { code: 31001, message: "daily budget too low", data: {} } }; });
  const ok = await client.callTool({ name: "update_budget", arguments: { campaign_id: "7001", daily_budget: 123.45 } });
  assert.equal(ok.isError, false);
  assert.deepEqual(JSON.parse(seen[1].init.body), { account_id: 51959, adgroup_id: 7001, daily_budget: 12345 });
  const bad = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "7001", action: "resume" } });
  assert.equal(bad.isError, true);
  assert.equal(JSON.parse(seen[2].init.body).configured_status, "AD_STATUS_NORMAL");
});
