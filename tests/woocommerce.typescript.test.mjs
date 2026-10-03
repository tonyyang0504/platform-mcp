import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/woocommerce.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const BASIC = "Basic " + Buffer.from("ck_key:cs_secret").toString("base64");

// The store host is a per-install config field resolved with the credentials, so exercise the real
// environment path (PLATFORM_MCP_WOOCOMMERCE_*) and the global fetch rather than an injected transport.
process.env.PLATFORM_MCP_WOOCOMMERCE_CONSUMER_KEY = "ck_key";
process.env.PLATFORM_MCP_WOOCOMMERCE_CONSUMER_SECRET = "cs_secret";
process.env.PLATFORM_MCP_WOOCOMMERCE_STORE_HOST = "shop.example";

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("woocommerce: tools follow the ecommerce_channels vocabulary (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["create_listing", "end_listing", "list_orders", "mark_shipped", "me", "set_inventory", "update_listing"]);
  const cl = tools.find((t) => t.name === "create_listing");
  assert.equal(cl.annotations.readOnlyHint, false);
  assert.equal(cl.annotations.destructiveHint, false);
  assert.deepEqual(cl.inputSchema.required, ["title", "price"]);
  assert.equal(tools.find((t) => t.name === "end_listing").annotations.destructiveHint, true);
  assert.equal(cl._meta["platform_mcp/endpoint"], "https://{store_host}/wp-json/wc/v3/products");
});

test("woocommerce: create_listing posts the documented product body with Basic auth to the configured store (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 201, body: { id: 794, permalink: "https://shop.example/product/premium-quality-19/", status: "publish", type: "simple", regular_price: "21.99", manage_stock: true, stock_quantity: 10 } }; });
  const res = await client.callTool({ name: "create_listing", arguments: { title: "Premium Quality", price: 21.99, sku: "PQ-1", quantity: 10, description: "Pellentesque habitant morbi" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.listing_id, "794");
  assert.equal(res.structuredContent.status, "publish");
  assert.equal(seen.url.href, "https://shop.example/wp-json/wc/v3/products");
  assert.equal(seen.init.method, "POST");
  assert.deepEqual(JSON.parse(seen.init.body), { name: "Premium Quality", type: "simple", regular_price: "21.99", description: "Pellentesque habitant morbi", sku: "PQ-1", stock_quantity: 10, manage_stock: true });
  assert.equal(seen.init.headers.Authorization, BASIC);
});

test("woocommerce: list_orders sends page/per_page/status/after and maps the order (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: [{ id: 727, status: "processing", currency: "USD", total: "29.35", date_created: "2017-03-22T16:28:02" }] }; });
  const res = await client.callTool({ name: "list_orders", arguments: { status: "processing", since: "2017-03-01T00:00:00", page: 2, limit: 50 } });
  assert.equal(res.isError, false);
  assert.equal(seen.origin + seen.pathname, "https://shop.example/wp-json/wc/v3/orders");
  assert.equal(seen.searchParams.get("page"), "2");
  assert.equal(seen.searchParams.get("per_page"), "50");
  assert.equal(seen.searchParams.get("status"), "processing");
  assert.equal(seen.searchParams.get("after"), "2017-03-01T00:00:00");
  assert.equal(res.structuredContent.orders[0].id, "727");
  assert.equal(res.structuredContent.orders[0].total, "29.35");
  assert.equal(res.structuredContent.next_page, null);
});

test("woocommerce: refused keys are an auth_error result (wire)", async () => {
  const client = await connect(() => ({ status: 401, body: { code: "woocommerce_rest_cannot_view", message: "Sorry, you cannot list resources.", data: { status: 401 } } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
});
