import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/theprintspace.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_token: "tok" }, 50, "test", fakeFetch(handler), SPEC.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["create_order", "get_order", "get_product", "list_products", "me", "quote_shipping"]);
});

test("quote_shipping posts one variant line (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { currency: "GBP", total_incl_vat: 54, delivery_cost: 10 } }; });
  const res = await client.callTool({ name: "quote_shipping", arguments: { product_id: "v9", country: "DE", quantity: 1 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.options[0].delivery_cost, 10);
  assert.equal(seen.url.pathname, "/v1/orders/quote");
  assert.deepEqual(JSON.parse(seen.init.body), { items: [{ variant_id: "v9", quantity: 1 }], delivery_country_code: "DE" });
  assert.equal(seen.init.headers.Authorization, "Bearer tok");
});

test("create_order maps delivery fields (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 201, body: { order_id: "o1", order_number: "CH1", currency: "GBP", total_incl_vat: 54 } }; });
  const res = await client.callTool({ name: "create_order", arguments: { items: [{ variant_id: "v9", quantity: 1 }], shipping_address: { name: "Ada", address1: "1 Main St", city: "London", country_code: "GB" } } });
  assert.equal(res.structuredContent.id, "o1");
  assert.equal(res.structuredContent.currency, "GBP");
  const body = JSON.parse(seen.init.body);
  assert.equal(body.delivery_name, "Ada");
  assert.equal(body.delivery_country_code, "GB");
});

test("401 is an auth error (wire)", async () => {
  const client = await connect(() => ({ status: 401, body: { detail: "invalid token" } }));
  const res = await client.callTool({ name: "get_product", arguments: { id: "p1" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
});
