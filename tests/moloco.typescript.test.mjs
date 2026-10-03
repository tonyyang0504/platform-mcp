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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/moloco.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_MOLOCO_API_KEY: "mol-api-key-secret" });

test("moloco get_report: api-key login then analytics-overview body (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.pathname === "/cm/v1/auth/tokens") return { body: { token: "MOLTOKEN", token_type: "AUTH_TOKEN" } };
    return { body: { rows: [{ date: "2026-09-01", campaign: { id: "c1" }, metric: { spend: 12.5 } }] } };
  });
  const res = await client.callTool({ name: "get_report", arguments: { account_id: "acc1", date_from: "2026-09-01", date_to: "2026-09-07" } });
  assert.equal(res.isError, false);
  assert.deepEqual(JSON.parse(seen[0].init.body), { api_key: "mol-api-key-secret" });
  assert.equal(seen[1].url.href, "https://api.moloco.cloud/cm/v1/analytics-overview");
  assert.equal(seen[1].init.headers.Authorization, "Bearer MOLTOKEN");
  assert.deepEqual(JSON.parse(seen[1].init.body).date_range, { start: "2026-09-01", end: "2026-09-07" });
  assert.equal(res.structuredContent.rows[0].spend, 12.5);
});
