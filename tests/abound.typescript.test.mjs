import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/abound.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const PRODUCT = { id: "5f1", title: "Ceramic Mug", brand: "Acme", images: [{ id: "i1", position: 0, source: "https://cdn.example.com/mug.jpg" }], variants: [{ id: "v1", sku: "MUG-1", basePrice: 6.5, baseCurrency: "USD", retailPrice: 14, inventoryAmount: 120 }] };

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
  const lp = tools.find((t) => t.name === "list_products");
  assert.equal(lp.annotations.readOnlyHint, true);
  assert.equal(lp.annotations.destructiveHint, false);
  assert.equal(lp.title, "List products");
  assert.equal(lp.inputSchema.additionalProperties, false);
  assert.equal(lp._meta["platform_mcp/endpoint"], "/buyer/products");
  assert.equal(lp._meta["platform_mcp/docs"], "https://developers.moderndropship.com/openapi/buyer-api.json");
});

test("list_products unwraps data and sends the raw Authorization key (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { data: [PRODUCT], hasMore: false } }; });
  const res = await client.callTool({ name: "list_products", arguments: { query: "mug", page: 3, limit: 20 } });
  assert.equal(res.isError, false);
  const p = res.structuredContent.products[0];
  assert.equal(p.id, "5f1");
  assert.equal(p.title, "Ceramic Mug");
  assert.equal(p.image_url, "https://cdn.example.com/mug.jpg");
  assert.equal(p.price, 6.5);
  assert.equal(p.sku, "MUG-1");
  assert.equal(p.stock, 120);
  assert.equal(res.structuredContent.next_page, null);
  assert.equal(seen.url.searchParams.get("page"), "2");
  assert.equal(seen.url.searchParams.get("limit"), "20");
  assert.equal(seen.url.searchParams.get("title"), "mug");
  assert.equal(seen.url.searchParams.has("companyId"), false);
  assert.equal(seen.init.headers.Authorization, "k");
});

test("get_order reads the first fulfillment tracking code (wire)", async () => {
  const client = await connect(() => ({ body: { data: { id: "o1", created: "2026-09-01T10:00:00Z", sellerOrders: [{ id: "so1", fulfilled: true, fulfillments: [{ carrier: "UPS", trackingCode: "1Z999", trackingUrls: [] }] }] } } }));
  const res = await client.callTool({ name: "get_order", arguments: { id: "o1" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "o1");
  assert.equal(res.structuredContent.created_at, "2026-09-01T10:00:00Z");
  assert.equal(res.structuredContent.tracking_number, "1Z999");
});

test("bad key is an isError auth result (wire)", async () => {
  const client = await connect(() => ({ status: 401, body: { error: [{ message: "unauthorized" }] } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
});
