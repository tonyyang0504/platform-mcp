import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/dreamship.json", import.meta.url), "utf8"));

async function connect(handler, creds = { api_key: "k" }) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fakeFetch(handler), SPEC.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("tools follow the vocabulary and carry annotations (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["create_order", "get_order", "get_product", "list_products", "me"]);
  const co = tools.find((t) => t.name === "create_order");
  assert.equal(co.annotations.destructiveHint, true);
  assert.equal(co._meta["platform_mcp/endpoint"], "/orders/");
});

test("list_products reads data + paging.count with the bearer key (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { paging: { count: 120, next: "n", previous: null }, data: [{ id: 101, name: "Unisex Tee", starting_basic_cost: "7.50" }] } }; });
  const res = await client.callTool({ name: "list_products", arguments: { page: 2, limit: 1 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.products[0].id, "101");
  assert.equal(res.structuredContent.products[0].title, "Unisex Tee");
  assert.equal(res.structuredContent.total, 120);
  assert.equal(res.structuredContent.next_page, 3);
  assert.equal(seen.url.pathname, "/v1/items/");
  assert.equal(seen.url.searchParams.get("page"), "2");
  assert.equal(seen.init.headers.Authorization, "Bearer k");
});

test("create_order sends address, line_items, shipping_method and the test flag (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 201, body: { id: 555, status: "submitted", created_at: "2026-09-24T10:00:00Z", total_cost: "12.40" } }; }, { api_key: "k", test_order: "true" });
  const res = await client.callTool({ name: "create_order", arguments: { items: [{ item_variant: 9001, quantity: 1, print_areas: [{ key: "front", url: "https://x.test/a.png" }] }], shipping_address: { first_name: "Jo", country: "US" }, shipping_option: "economy" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "555");
  const body = JSON.parse(seen.init.body);
  assert.deepEqual(Object.keys(body).sort(), ["address", "line_items", "shipping_method", "test_order"]);
  assert.equal(body.test_order, "true");
});

test("get_order maps the first tracking number (wire)", async () => {
  const client = await connect(() => ({ body: { id: 555, status: "fulfilled", created_at: "2026-09-24T10:00:00Z", fulfillments: [{ trackings: [{ tracking_number: "9400" }] }] } }));
  const res = await client.callTool({ name: "get_order", arguments: { id: "555" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.tracking_number, "9400");
});
