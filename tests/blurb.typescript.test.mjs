import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/blurb.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_key: "key-1", shared_secret: "secret-1" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("tools follow the vocabulary and carry annotations (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["create_order", "get_order", "me"]);
  const co = tools.find((t) => t.name === "create_order");
  assert.equal(co.annotations.readOnlyHint, false);
  assert.equal(co.annotations.destructiveHint, true);
  assert.equal(co.title, "Create an order");
  assert.deepEqual(co.inputSchema.required, ["items", "shipping_address"]);
  assert.equal(co._meta["platform_mcp/endpoint"], "/orders/create");
  assert.equal(co._meta["platform_mcp/docs"], "https://docs.api.rpiprint.com/api-reference");
});

test("me lists orders with HTTP Basic key:secret (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { totalCount: 0, offset: 0, limit: 10, nextOffset: null, orders: [] } }; });
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.ok, true);
  assert.equal(seen.url.pathname, "/orders");
  assert.equal(seen.url.searchParams.get("limit"), "10");
  assert.equal(seen.init.headers.Authorization, "Basic " + Buffer.from("key-1:secret-1").toString("base64"));
});

test("create_order sends the documented body in USD and reads customerOrderId (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 201, body: { customerOrderId: "ORD-77", statusCode: 201, statusDescription: "Order received" } }; });
  const res = await client.callTool({ name: "create_order", arguments: { items: [{ sku: "HC_8x10_LAND", quantity: 1, product: { coverUrl: "https://example.com/c.pdf", gutsUrl: "https://example.com/g.pdf" } }], shipping_address: { name: "J Smith", address1: "1 St", city: "Seattle", postal: "98101", country: "US", regionCode: "WA" }, shipping_option: "standard" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "ORD-77");
  assert.equal(res.structuredContent.status, "Order received");
  const body = JSON.parse(seen.init.body);
  assert.deepEqual(Object.keys(body).sort(), ["currency", "destination", "orderItems", "shippingClassification"]);
  assert.equal(body.currency, "USD");
  assert.equal(body.shippingClassification, "standard");
  assert.equal(body.destination.regionCode, "WA");
});

test("get_order reads nested status, pricing and tracking (wire)", async () => {
  const client = await connect(() => ({ body: { order: { customerOrderId: "ORD-77", status: "SHIPPED" }, pricing: { orderTotal: 41.2, currency: "USD" }, shipmentTracking: [{ trackingNumber: "9400111", shipMethod: "USPS" }] } }));
  const res = await client.callTool({ name: "get_order", arguments: { id: "ORD-77" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "ORD-77");
  assert.equal(res.structuredContent.status, "SHIPPED");
  assert.equal(res.structuredContent.total, 41.2);
  assert.equal(res.structuredContent.tracking_number, "9400111");
});
