import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/marketplaces/paddle.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler, creds = { api_key: "pdl_test_secret" }) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("paddle: tools follow the marketplaces vocabulary (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["create_product", "get_product", "list_products", "list_refunds", "list_sales", "me", "refund", "update_price"]);
  const rf = tools.find((t) => t.name === "refund");
  assert.equal(rf.annotations.readOnlyHint, false);
  assert.equal(rf.annotations.destructiveHint, true);
  assert.deepEqual(rf.inputSchema.required, ["sale_id"]);
  assert.equal(tools.find((t) => t.name === "update_price")._meta["platform_mcp/endpoint"], "/prices");
  assert.equal(tools.find((t) => t.name === "list_sales").annotations.readOnlyHint, true);
});

test("paddle: list_products sends include=prices and maps the first unit price (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { data: [{ id: "pro_01", name: "AeroEdit Pro", description: "Professional plan", status: "active", created_at: "2023-02-23T12:43:46.605Z", updated_at: "2024-04-05T15:53:44.687Z", prices: [{ id: "pri_01", unit_price: { amount: "1000", currency_code: "USD" }, status: "active" }] }], meta: { pagination: { per_page: 10, has_more: false, estimated_total: 1 } } } }; });
  const res = await client.callTool({ name: "list_products", arguments: { status: "active", limit: 10 } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.origin + seen.url.pathname, "https://api.paddle.com/products");
  assert.equal(seen.url.searchParams.get("include"), "prices");
  assert.equal(seen.url.searchParams.get("per_page"), "10");
  assert.equal(seen.url.searchParams.get("status"), "active");
  assert.equal(seen.init.headers.Authorization, "Bearer pdl_test_secret");
  assert.equal(res.structuredContent.products[0].id, "pro_01");
  assert.equal(res.structuredContent.products[0].price, "1000");
  assert.equal(res.structuredContent.products[0].currency, "USD");
  assert.equal(res.structuredContent.next_page, null);
});

test("paddle: update_price posts the documented unit_price object; refund is a full adjustment (wire)", async () => {
  let seen;
  let client = await connect((url, init) => { seen = { url, init }; return { status: 201, body: { data: { id: "pri_02", product_id: "pro_01", unit_price: { amount: "1500", currency_code: "USD" }, status: "active", created_at: "2024-04-05T15:53:44.687Z", updated_at: "2024-04-05T15:53:44.687Z" } } }; });
  let res = await client.callTool({ name: "update_price", arguments: { product_id: "pro_01", price: 1500, currency: "USD" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "pro_01");
  assert.equal(res.structuredContent.price, "1500");
  assert.equal(seen.init.method, "POST");
  assert.deepEqual(JSON.parse(seen.init.body), { description: "Price created via platform-mcp update_price", product_id: "pro_01", unit_price: { amount: "1500", currency_code: "USD" } });
  client = await connect((url, init) => { seen = { url, init }; return { status: 201, body: { data: { id: "adj_01", action: "refund", type: "full", transaction_id: "txn_01", status: "pending_approval", currency_code: "USD", totals: { total: "1000", currency_code: "USD" }, created_at: "2024-04-13T10:18:47Z" } } }; });
  res = await client.callTool({ name: "refund", arguments: { sale_id: "txn_01", amount: 5, reason: "duplicate" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "adj_01");
  assert.equal(res.structuredContent.sale_id, "txn_01");
  assert.equal(seen.url.pathname, "/adjustments");
  assert.deepEqual(JSON.parse(seen.init.body), { action: "refund", transaction_id: "txn_01", reason: "duplicate", type: "full" });
});

test("paddle: refused key is an auth_error result without the secret (wire)", async () => {
  const client = await connect(() => ({ status: 403, body: { error: { type: "request_error", code: "forbidden", detail: "token=pdl_test_secret is not allowed" } } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.equal(JSON.stringify(res.structuredContent).includes("pdl_test_secret"), false);
});
