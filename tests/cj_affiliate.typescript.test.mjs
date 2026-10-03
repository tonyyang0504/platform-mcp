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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/cj_affiliate.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_CJ_AFFILIATE_PERSONAL_ACCESS_TOKEN: "cj-pat-secret", PLATFORM_MCP_CJ_AFFILIATE_COMPANY_ID: "11223344" });

test("cj_affiliate get_report: GraphQL JSON body with variables (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { data: { advertiserCommissions: { count: 1, records: [{ commissionId: "9", advCommissionAmountAdvCurrency: "7.55" }] } } } }; });
  const res = await client.callTool({ name: "get_report", arguments: { account_id: "11223344", date_from: "2026-09-01", date_to: "2026-09-08" } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].url.href, "https://commissions.api.cj.com/query");
  assert.equal(seen[0].init.headers.Authorization, "Bearer cj-pat-secret");
  assert.deepEqual(JSON.parse(seen[0].init.body).variables, { advertisers: ["11223344"], since: "2026-09-01T00:00:00Z", before: "2026-09-08T00:00:00Z" });
  assert.equal(res.structuredContent.rows[0].spend, "7.55");
});
