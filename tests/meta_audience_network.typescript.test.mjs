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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/meta_audience_network.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_META_AUDIENCE_NETWORK_ACCESS_TOKEN: "EAANTOKEN" });

test("meta_audience_network get_report: adnetworkanalytics query (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { data: [{ results: [{ time: "2026-09-01T07:00:00+0000", metric: "fb_ad_network_imp", value: "1200" }] }] } }; });
  const res = await client.callTool({ name: "get_report", arguments: { account_id: "9876", date_from: "2026-09-01", date_to: "2026-09-07" } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].url.pathname, "/v25.0/9876/adnetworkanalytics");
  assert.equal(seen[0].url.searchParams.get("aggregation_period"), "day");
  assert.equal(seen[0].init.headers.Authorization, "Bearer EAANTOKEN");
  assert.equal(res.structuredContent.rows[0].value, "1200");
});
