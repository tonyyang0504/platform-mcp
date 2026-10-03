import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/marketplaces/digistore24.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler, creds = { api_key: "ds24_test_secret" }) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("digistore24: every marketplaces verb is served (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["create_product", "get_product", "get_sales_stats", "list_products", "list_refunds", "list_sales", "me", "refund", "update_price"]);
  const rf = tools.find((t) => t.name === "refund");
  assert.equal(rf.annotations.destructiveHint, true);
  assert.equal(rf._meta["platform_mcp/endpoint"], "/refundPurchase");
  assert.equal(tools.find((t) => t.name === "list_sales").annotations.readOnlyHint, true);
  assert.equal(tools.find((t) => t.name === "update_price").annotations.destructiveHint, false);
});

test("digistore24: list_sales sends the documented query with the X-DS-API-KEY header and maps purchases (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { api_version: "1.234", result: "success", data: { purchase_list: [{ purchase_id: "X26QE8GN", product_id: 39, product_name: "The Weight Loss Cake", amount: 29.9, currency: "EUR", payment_status: "paid", buyer_email: "uw@ds24mail.com", created_at: "2026-09-20 12:00:00" }] } } }; });
  const res = await client.callTool({ name: "list_sales", arguments: { since: "2026-09-01", product_id: "39", page: 2, limit: 50 } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.origin + seen.url.pathname, "https://www.digistore24.com/api/call/listPurchases");
  assert.equal(seen.url.searchParams.get("from"), "2026-09-01");
  assert.equal(seen.url.searchParams.get("search[product_id]"), "39");
  assert.equal(seen.url.searchParams.get("page_no"), "2");
  assert.equal(seen.url.searchParams.get("page_size"), "50");
  assert.equal(seen.url.searchParams.get("sort_order"), "desc");
  assert.equal(seen.init.headers["X-DS-API-KEY"], "ds24_test_secret");
  assert.equal("Authorization" in seen.init.headers, false);
  const s = res.structuredContent.sales[0];
  assert.equal(s.id, "X26QE8GN");
  assert.equal(s.product_id, "39");
  assert.equal(s.amount, 29.9);
  assert.equal(s.customer_email, "uw@ds24mail.com");
});

test("digistore24: create_product passes data[...] parameters without a JSON body; refund targets the purchase (wire)", async () => {
  let seen;
  let client = await connect((url, init) => { seen = { url, init }; return { body: { result: "success", data: { product_id: 4711 } } }; });
  let res = await client.callTool({ name: "create_product", arguments: { name: "Cake Course", description: "<p>Learn</p>", price: 49, currency: "EUR", url: "https://example.com/cake" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "4711");
  assert.equal(seen.init.method, "POST");
  assert.equal(seen.init.body, undefined);
  assert.equal(seen.url.pathname, "/api/call/createProduct");
  assert.equal(seen.url.searchParams.get("data[name_intern]"), "Cake Course");
  assert.equal(seen.url.searchParams.get("data[description_en]"), "<p>Learn</p>");
  assert.equal(seen.url.searchParams.get("data[currency]"), "EUR");
  assert.equal(seen.url.searchParams.get("data[salespage_url]"), "https://example.com/cake");
  assert.equal(seen.init.headers["X-DS-API-KEY"], "ds24_test_secret");
  client = await connect((url, init) => { seen = { url, init }; return { body: { result: "success", data: { status: "pending", modified: "Y", note: "Refund is being processed" } } }; });
  res = await client.callTool({ name: "refund", arguments: { sale_id: "X26QE8GN", amount: 10, reason: "buyer request" } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.pathname, "/api/call/refundPurchase");
  assert.equal(seen.url.searchParams.get("purchase_id"), "X26QE8GN");
  assert.equal(seen.url.searchParams.has("amount"), false);
  assert.equal(res.structuredContent.id, "refundPurchase");
  assert.equal(res.structuredContent.raw.status, "pending");
});

test("digistore24: refused key is an auth_error result without the secret (wire)", async () => {
  const client = await connect(() => ({ status: 401, body: { result: "error", message: "Invalid api_key=ds24_test_secret", code: "unauthorized" } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.equal(JSON.stringify(res.structuredContent).includes("ds24_test_secret"), false);
});
