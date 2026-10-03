import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/pwinty.json", import.meta.url), "utf8"));

test("X-API-Key and one-item quote body (wire)", async () => {
  let seen;
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_key: "k" }, 50, "test", fakeFetch((url, init) => { seen = { url, init }; return { body: { outcome: "Created", quotes: [{ shipmentMethod: "Standard", costSummary: { items: { amount: "10.00", currency: "USD" }, shipping: { amount: "4.50", currency: "USD" } } }] } }; }), SPEC.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  const res = await client.callTool({ name: "quote_shipping", arguments: { product_id: "GLOBAL-FAP-10x10", country: "US", quantity: 1 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.options[0].shipping_cost, "4.50");
  assert.equal(seen.url.pathname, "/v4.0/quotes");
  assert.equal(seen.init.headers["X-API-Key"], "k");
  assert.deepEqual(JSON.parse(seen.init.body).items, [{ sku: "GLOBAL-FAP-10x10", copies: 1, assets: [{ printArea: "default" }] }]);
});
