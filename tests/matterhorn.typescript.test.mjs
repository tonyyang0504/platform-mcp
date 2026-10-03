import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/matterhorn.json", import.meta.url), "utf8"));

test("get_order maps shipping number and totals (wire)", async () => {
  let seen;
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_key: "K" }, 50, "test", fakeFetch((url, init) => { seen = { url, init }; return { body: { id: "67062", status: "Sent", order_currency: "EUR", total_gross: 95.86, shipping_number: "GLS123", shipping_service: "GLS", order_date: "2023-10-04 09:14:07" } }; }), SPEC.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  const res = await client.callTool({ name: "get_order", arguments: { id: "67062" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.tracking_number, "GLS123");
  assert.equal(res.structuredContent.total, 95.86);
  assert.equal(seen.url.pathname, "/B2BAPI/ACCOUNT/ORDERS/67062");
  assert.equal(seen.init.headers.Authorization, "K");
});
