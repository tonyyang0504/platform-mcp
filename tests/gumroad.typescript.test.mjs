import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/marketplaces/gumroad.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler, creds = { access_token: "gum_test_secret" }) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fakeFetch(handler), SPEC.adapter.envelope));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("gumroad: tools follow the marketplaces vocabulary (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["create_product", "get_product", "list_products", "list_sales", "me", "refund", "update_price"]);
  const cp = tools.find((t) => t.name === "create_product");
  assert.equal(cp.annotations.readOnlyHint, false);
  assert.equal(cp.annotations.destructiveHint, false);
  assert.deepEqual(cp.inputSchema.required, ["name", "price", "currency"]);
  assert.equal(tools.find((t) => t.name === "refund").annotations.destructiveHint, true);
  assert.equal(tools.find((t) => t.name === "list_sales")._meta["platform_mcp/endpoint"], "/sales");
});

test("gumroad: list_sales sends after/product_id with the bearer token and maps the sale (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { success: true, next_page_key: "k", sales: [{ id: "B28UKN", email: "calvin@gumroad.com", created_at: "2021-01-05T19:38:56Z", product_name: "Pencil Icon PSD", price: 1000, currency: "usd", product_id: "32-nP", refunded: false, partially_refunded: false }] } }; });
  const res = await client.callTool({ name: "list_sales", arguments: { since: "2020-09-03", product_id: "32-nP", page: 3, limit: 20 } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.origin + seen.url.pathname, "https://api.gumroad.com/v2/sales");
  assert.equal(seen.url.searchParams.get("after"), "2020-09-03");
  assert.equal(seen.url.searchParams.get("product_id"), "32-nP");
  assert.equal(seen.url.searchParams.has("page"), false);
  assert.equal(seen.url.searchParams.has("access_token"), false);
  assert.equal(seen.init.headers.Authorization, "Bearer gum_test_secret");
  const s = res.structuredContent.sales[0];
  assert.equal(s.id, "B28UKN");
  assert.equal(s.amount, 1000);
  assert.equal(s.customer_email, "calvin@gumroad.com");
  assert.equal(s.refunded, false);
});

test("gumroad: create_product posts a draft with the price in cents; refund sends amount_cents (wire)", async () => {
  let seen;
  let client = await connect((url, init) => { seen = { url, init }; return { body: { success: true, product: { id: "A-m3", name: "Pencil Icon PSD", price: 100, currency: "usd", published: false, short_url: "https://sahil.gumroad.com/l/pencil" } } }; });
  let res = await client.callTool({ name: "create_product", arguments: { name: "Pencil Icon PSD", price: 100, currency: "usd" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "A-m3");
  assert.equal(res.structuredContent.url, "https://sahil.gumroad.com/l/pencil");
  assert.equal(seen.init.method, "POST");
  assert.deepEqual(JSON.parse(seen.init.body), { name: "Pencil Icon PSD", price: 100, price_currency_type: "usd", draft: true });
  client = await connect((url, init) => { seen = { url, init }; return { body: { success: true, sale: { id: "A-m3", price: 1000, currency: "usd", created_at: "2021-01-23T18:24:07Z", partially_refunded: true } } }; });
  res = await client.callTool({ name: "refund", arguments: { sale_id: "A-m3", amount: 200 } });
  assert.equal(res.isError, false);
  assert.equal(seen.init.method, "PUT");
  assert.equal(seen.url.pathname, "/v2/sales/A-m3/refund");
  assert.deepEqual(JSON.parse(seen.init.body), { amount_cents: 200 });
  assert.equal(res.structuredContent.sale_id, "A-m3");
});

test("gumroad: a success:false body is an upstream_error and a refused token an auth_error without the secret (wire)", async () => {
  let client = await connect(() => ({ status: 200, body: { success: false, message: "The product could not be found." } }));
  let res = await client.callTool({ name: "get_product", arguments: { product_id: "nope" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "upstream_error");
  client = await connect(() => ({ status: 401, body: { success: false, message: "access_token=gum_test_secret is invalid" } }));
  res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.equal(JSON.stringify(res.structuredContent).includes("gum_test_secret"), false);
});
