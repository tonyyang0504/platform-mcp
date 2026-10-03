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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/tiktok.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_TIKTOK_ACCESS_TOKEN: "act.tok", PLATFORM_MCP_TIKTOK_APP_ID: "7001", PLATFORM_MCP_TIKTOK_SECRET: "appsecret9", PLATFORM_MCP_TIKTOK_ADVERTISER_ID: "6900" });

test("tiktok get_report sends Access-Token and the fixed JSON-array params (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { code: 0, message: "OK", data: { list: [{ dimensions: { campaign_id: "1800", stat_time_day: "2026-09-01 00:00:00" }, metrics: { spend: "12.50", impressions: "900", clicks: "31" } }] } } }; });
  const res = await client.callTool({ name: "get_report", arguments: { account_id: "6900", date_from: "2026-09-01", date_to: "2026-09-07" } });
  assert.equal(res.isError, false);
  const u = seen[0].url;
  assert.equal(u.pathname, "/open_api/v1.3/report/integrated/get/");
  assert.equal(seen[0].init.headers["Access-Token"], "act.tok");
  assert.deepEqual(JSON.parse(u.searchParams.get("dimensions")), ["campaign_id", "stat_time_day"]);
  assert.equal(u.searchParams.get("data_level"), "AUCTION_CAMPAIGN");
  assert.equal(u.searchParams.get("start_date"), "2026-09-01");
  const r = res.structuredContent.rows[0];
  assert.equal(r.campaign_id, "1800"); assert.equal(r.spend, "12.50");
});

test("tiktok update_budget uses the configured advertiser; a non-zero code is an error (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { code: 40002, message: "Budget below minimum", data: {} } }; });
  const res = await client.callTool({ name: "update_budget", arguments: { campaign_id: "1800", daily_budget: 1 } });
  assert.deepEqual(JSON.parse(seen[0].init.body), { advertiser_id: "6900", campaign_id: "1800", budget: 1 });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "upstream_error"); // auth audit: the code/message envelope surfaces the platform's message
  assert.match(res.structuredContent.message, /Budget below minimum/);
});

test("tiktok pause_resume posts campaign_ids as an array and ENABLE for resume (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { code: 0, message: "OK", data: { status: "ENABLE", campaign_ids: ["1800"] } } }; });
  const res = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "1800", action: "resume" } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].url.pathname, "/open_api/v1.3/campaign/status/update/");
  assert.deepEqual(JSON.parse(seen[0].init.body), { advertiser_id: "6900", campaign_ids: ["1800"], operation_status: "ENABLE" });
  assert.equal(res.structuredContent.status, "ENABLE");
});
