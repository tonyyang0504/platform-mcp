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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/awin.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_AWIN_API_TOKEN: "awin-secret-token" });

test("awin get_report: bearer, publisher report query (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: [{ publisherId: 55, totalComm: 8 }] }; });
  const res = await client.callTool({ name: "get_report", arguments: { account_id: "1001", date_from: "2026-09-01", date_to: "2026-09-07" } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].url.pathname, "/advertisers/1001/reports/publisher");
  assert.equal(seen[0].url.searchParams.get("startDate"), "2026-09-01");
  assert.equal(seen[0].url.searchParams.get("timezone"), "UTC");
  assert.equal(seen[0].init.headers.Authorization, "Bearer awin-secret-token");
  assert.equal(res.structuredContent.rows[0].spend, 8);
});
