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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/kelkoo_group.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_KELKOO_GROUP_JWT: "kk-jwt-secret" });

test("kelkoo_group get_report: bearer JWT, category statistics path (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: [{ campaignId: 1000000000, date: "2021-03-15", clicks: 7, cost: 1.3566 }] }; });
  const res = await client.callTool({ name: "get_report", arguments: { account_id: "x", campaign_id: "1000000000", date_from: "2021-03-15", date_to: "2021-03-16" } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].url.href, "https://api.kelkoogroup.net/merchant/statistics/v1/category/1000000000?startDate=2021-03-15&endDate=2021-03-16");
  assert.equal(seen[0].init.headers.Authorization, "Bearer kk-jwt-secret");
  assert.equal(res.structuredContent.rows[0].spend, 1.3566);
});
