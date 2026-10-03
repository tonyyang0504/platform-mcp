import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/gelato.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const UID = "cards_pf_bb_pt_110-lb-cover-uncoated_cl_4-0_hor";

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_key: "k" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("tools follow the vocabulary and carry annotations (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_order", "get_product", "list_products", "me"]);
  const go = tools.find((t) => t.name === "get_order");
  assert.equal(go.annotations.readOnlyHint, true);
  assert.equal(go.title, "Get an order");
  assert.deepEqual(go.inputSchema.required, ["id"]);
  assert.equal(go._meta["platform_mcp/endpoint"], "/v4/orders/{orderId}");
  assert.equal(go._meta["platform_mcp/docs"], "https://dashboard.gelato.com/docs/orders/v4/get/");
});

test("list_products posts the search to the product host with X-API-KEY (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { products: [{ productUid: UID, attributes: { Orientation: "hor" } }], hits: { attributeHits: {} } } }; });
  const res = await client.callTool({ name: "list_products", arguments: { category: "posters", page: 2, limit: 50 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.products[0].id, UID);
  assert.equal(res.structuredContent.products[0].title, UID);
  assert.equal(seen.url.href, "https://product.gelatoapis.com/v3/catalogs/posters/products:search");
  assert.equal(seen.init.method, "POST");
  assert.deepEqual(JSON.parse(seen.init.body), { limit: 50, offset: 50 });
  assert.equal(seen.init.headers["X-API-KEY"], "k");
  assert.equal("Authorization" in seen.init.headers, false);
});

test("get_order maps status, total and tracking (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { id: "37365096", fulfillmentStatus: "printed", financialStatus: "paid", currency: "USD", createdAt: "2021-01-14T10:32:03+00:00", shipment: { packages: [{ trackingCode: "12345678990" }] }, receipts: [{ totalInclVat: 33.45 }] } }; });
  const res = await client.callTool({ name: "get_order", arguments: { id: "37365096" } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.href, "https://order.gelatoapis.com/v4/orders/37365096");
  assert.equal(res.structuredContent.status, "printed");
  assert.equal(res.structuredContent.total, 33.45);
  assert.equal(res.structuredContent.currency, "USD");
  assert.equal(res.structuredContent.tracking_number, "12345678990");
});

test("rate limit is an isError result, not a protocol error (wire)", async () => {
  const client = await connect(() => ({ status: 429, headers: { "Retry-After": "10" }, body: { message: "Too Many Requests" } }));
  const res = await client.callTool({ name: "get_product", arguments: { id: UID } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
  assert.equal(res.structuredContent.retry_after_seconds, 10);
});
