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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/impact_com.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_IMPACT_COM_ACCOUNT_SID: "IRabc123", PLATFORM_MCP_IMPACT_COM_AUTH_TOKEN: "imp-auth-secret", PLATFORM_MCP_IMPACT_COM_REPORT_ID: "adv_perf_by_day" });

test("impact_com get_report: SID in base path, basic auth, report query (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { Records: [{ Clicks: "10" }] } }; });
  const res = await client.callTool({ name: "get_report", arguments: { account_id: "x", campaign_id: "1234", date_from: "2026-09-01", date_to: "2026-09-07" } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].url.pathname, "/Advertisers/IRabc123/Reports/adv_perf_by_day");
  assert.equal(seen[0].url.searchParams.get("SUBAID"), "1234");
  assert.equal(seen[0].init.headers.Authorization, "Basic " + Buffer.from("IRabc123:imp-auth-secret").toString("base64"));
  assert.equal(res.structuredContent.rows[0].raw.Clicks, "10");
});
