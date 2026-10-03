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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/applovin.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_APPLOVIN_CAMPAIGN_API_KEY: "cm-secret-key", PLATFORM_MCP_APPLOVIN_REPORT_KEY: "rep-secret-key", PLATFORM_MCP_APPLOVIN_ACCOUNT_ID: "777" });

test("applovin pause_resume: raw Authorization key, account_id query, status body (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { id: "12345" } }; });
  const res = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "12345", action: "resume" } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].init.method, "POST");
  assert.equal(seen[0].url.href, "https://api.ads.axon.ai/manage/v1/campaign/update?account_id=777");
  assert.equal(seen[0].init.headers.Authorization, "cm-secret-key");
  assert.deepEqual(JSON.parse(seen[0].init.body), { id: "12345", type: "APP", status: "LIVE" });
});

test("applovin get_report reads results from the reporting host (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { code: 200, results: [{ day: "2026-09-01", cost: "12.50" }] } }; });
  const res = await client.callTool({ name: "get_report", arguments: { account_id: "777", date_from: "2026-09-01", date_to: "2026-09-07" } });
  assert.equal(seen[0].url.host, "r.applovin.com");
  assert.equal(seen[0].url.searchParams.get("api_key"), "rep-secret-key");
  assert.equal(res.structuredContent.rows[0].spend, "12.50");
});
