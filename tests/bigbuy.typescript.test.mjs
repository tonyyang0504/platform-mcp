import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/bigbuy.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler, creds = { api_key: "k" }) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("tools follow the vocabulary and carry annotations (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["create_order", "get_order", "get_product", "list_products", "me", "track"]);
  const co = tools.find((t) => t.name === "create_order");
  assert.equal(co.annotations.readOnlyHint, false);
  assert.equal(co.annotations.destructiveHint, true);
  assert.equal(co.title, "Create an order");
  assert.deepEqual(co.inputSchema.required, ["items", "shipping_address"]);
  assert.equal(co._meta["platform_mcp/endpoint"], "/rest/order/create.json");
  const lp = tools.find((t) => t.name === "list_products");
  assert.equal(lp.annotations.readOnlyHint, true);
  assert.equal(lp.outputSchema.properties.products.type, "array");
});

test("list_products maps documented fields, zero-based pages and the bearer key (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: [{ id: 1234, sku: "S12435678", name: "Wire Scalp Massager", description: "<p>...</p>", url: "wire-scalp-massager", isoCode: "en" }] }; }, { api_key: "k", iso_code: "en" });
  const res = await client.callTool({ name: "list_products", arguments: { category: "11548", page: 2, limit: 50 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.products[0].id, "1234");
  assert.equal(res.structuredContent.products[0].title, "Wire Scalp Massager");
  assert.equal(res.structuredContent.products[0].sku, "S12435678");
  assert.equal(res.structuredContent.next_page, null);
  assert.equal(seen.url.pathname, "/rest/catalog/productsinformation.json");
  assert.equal(seen.url.searchParams.get("page"), "1");
  assert.equal(seen.url.searchParams.get("pageSize"), "50");
  assert.equal(seen.url.searchParams.get("parentTaxonomy"), "11548");
  assert.equal(seen.url.searchParams.get("isoCode"), "en");
  assert.equal(seen.init.headers.Authorization, "Bearer k");
});

test("create_order nests the body under order and reads order_id (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 201, body: { order_id: 123456 } }; }, { api_key: "k", payment_method: "moneybox" });
  const res = await client.callTool({ name: "create_order", arguments: { items: [{ reference: "S12435678", quantity: 2 }], shipping_address: { firstName: "A", lastName: "L", country: "ES", postcode: "46011", town: "Valencia", address: "Road 14", phone: "789456123", email: "a@example.com" } } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "123456");
  const body = JSON.parse(seen.init.body);
  assert.deepEqual(Object.keys(body), ["order"]);
  assert.equal(body.order.products[0].reference, "S12435678");
  assert.equal(body.order.shippingAddress.country, "ES");
  assert.equal(body.order.paymentMethod, "moneybox");
  assert.equal("carriers" in body.order, false);
});

test("rate limit is an isError result, not a protocol error (wire)", async () => {
  const client = await connect(() => ({ status: 429, headers: { "Retry-After": "30" }, body: { code: 429, message: "Exceeded requests limits." } }));
  const res = await client.callTool({ name: "get_order", arguments: { id: "123456" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
  assert.equal(res.structuredContent.retry_after_seconds, 30);
});
