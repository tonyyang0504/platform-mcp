import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/orosy.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_key: "orosy_live_SECRET" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_order", "get_product", "list_products", "me", "quote_shipping", "track"]);
});

test("get_product maps the first variation and sends the bearer key (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { product_id: "p-1", title: "タオル", brand: "B", product_number: "T-01", images: [{ url: "https://cdn/x.jpg", is_primary: true }], variations: [{ variation_id: "v1", buyer_price: 480, currency: "JPY", stock_qty: 12, order_unit: "6" }], delivery_group: { min_order_amount: 5000 }, orderable: true } }; });
  const res = await client.callTool({ name: "get_product", arguments: { id: "p-1" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.price, 480);
  assert.equal(res.structuredContent.stock, 12);
  assert.equal(res.structuredContent.image_url, "https://cdn/x.jpg");
  assert.equal(seen.url.pathname, "/v1/products/p-1");
  assert.equal(seen.init.headers.Authorization, "Bearer orosy_live_SECRET");
});

test("rate limit is an isError result (wire)", async () => {
  const client = await connect(() => ({ status: 429, headers: { "Retry-After": "10" }, body: { error: "too many requests" } }));
  const res = await client.callTool({ name: "list_products", arguments: { query: "タオル" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
});
