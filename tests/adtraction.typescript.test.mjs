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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/adtraction.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_ADTRACTION_API_TOKEN: "adt-secret-token" });

test("adtraction get_report: X-Token header, POST daily statistics (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    return { body: [{ date: "2026-09-01", clicks: 120, cost: 45.5, impressions: 3000 }] };
  });
  const res = await client.callTool({ name: "get_report", arguments: { account_id: "x", date_from: "2026-09-01", date_to: "2026-09-07" } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].init.method, "POST");
  assert.equal(seen[0].url.href, "https://api.adtraction.net/v2/advertiser/statistics/days/");
  assert.equal(seen[0].init.headers["X-Token"], "adt-secret-token");
  assert.deepEqual(JSON.parse(seen[0].init.body), { fromDate: "2026-09-01", toDate: "2026-09-07", transactionStatus: 3 });
  assert.equal(res.structuredContent.rows[0].spend, 45.5);
});
