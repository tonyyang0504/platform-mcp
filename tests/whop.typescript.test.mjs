import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/marketplaces/whop.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const CREDS = { api_key: "whop_test_secret", company_id: "biz_1" };

async function connect(handler, creds = CREDS) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("whop: tools follow the marketplaces vocabulary (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["create_product", "get_product", "list_products", "list_refunds", "list_sales", "me", "refund", "update_price"]);
  const cp = tools.find((t) => t.name === "create_product");
  assert.equal(cp.annotations.readOnlyHint, false);
  assert.equal(cp.annotations.destructiveHint, false);
  assert.deepEqual(cp.inputSchema.required, ["name", "price", "currency"]);
  assert.equal(tools.find((t) => t.name === "refund").annotations.destructiveHint, true);
  assert.equal(tools.find((t) => t.name === "list_sales")._meta["platform_mcp/endpoint"], "/payments");
});

test("whop: list_sales scopes to the company and maps the payment (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { data: [{ id: "pay_1", status: "paid", total: 29, currency: "usd", product: { id: "prod_1", title: "Pickaxe Analytics" }, user: { id: "user_1", email: "john@example.com" }, created_at: "2023-12-01T05:00:00.401Z", refunded_amount: 0 }], page_info: { has_next_page: false } } }; });
  const res = await client.callTool({ name: "list_sales", arguments: { product_id: "prod_1", since: "2023-11-01T00:00:00Z", limit: 10 } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.origin + seen.url.pathname, "https://api.whop.com/api/v1/payments");
  assert.equal(seen.url.searchParams.get("account_id"), "biz_1");
  assert.equal(seen.url.searchParams.get("first"), "10");
  assert.equal(seen.url.searchParams.get("created_after"), "2023-11-01T00:00:00Z");
  assert.equal(seen.url.searchParams.get("product_ids"), "prod_1");
  assert.equal(seen.init.headers.Authorization, "Bearer whop_test_secret");
  const s = res.structuredContent.sales[0];
  assert.equal(s.id, "pay_1");
  assert.equal(s.product_name, "Pickaxe Analytics");
  assert.equal(s.amount, 29);
  assert.equal(s.customer_email, "john@example.com");
  assert.equal(res.structuredContent.next_page, null);
});

test("whop: create_product nests plan_options and refund sends partial_amount (wire)", async () => {
  let seen;
  let client = await connect((url, init) => { seen = { url, init }; return { body: { id: "prod_new", title: "Pro Plan", description: "d", visibility: "visible", created_at: "2023-12-01T05:00:00.401Z", updated_at: "2023-12-01T05:00:00.401Z" } }; });
  let res = await client.callTool({ name: "create_product", arguments: { name: "Pro Plan", description: "d", price: 10.43, currency: "usd" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "prod_new");
  assert.equal(res.structuredContent.status, "visible");
  assert.equal(seen.init.method, "POST");
  assert.deepEqual(JSON.parse(seen.init.body), { account_id: "biz_1", title: "Pro Plan", description: "d", plan_options: { initial_price: 10.43, base_currency: "usd", plan_type: "one_time" } });
  client = await connect((url, init) => { seen = { url, init }; return { body: { id: "pay_1", status: "paid", currency: "usd", refunded_amount: 6.9, refunded_at: "2024-01-02T00:00:00Z" } }; });
  res = await client.callTool({ name: "refund", arguments: { sale_id: "pay_1", amount: 6.9, reason: "goodwill" } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.pathname, "/api/v1/payments/pay_1/refund");
  assert.deepEqual(JSON.parse(seen.init.body), { partial_amount: 6.9 });
  assert.equal(res.structuredContent.amount, 6.9);
  assert.equal(res.structuredContent.sale_id, "pay_1");
});

test("whop: refused key is an auth_error result without the secret (wire)", async () => {
  const client = await connect(() => ({ status: 401, body: { error: { message: "Unauthorized: token=whop_test_secret" } } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.equal(JSON.stringify(res.structuredContent).includes("whop_test_secret"), false);
});
