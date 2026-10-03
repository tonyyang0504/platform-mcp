import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/tvcmall.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler, creds = { authorization_token: "tok==" }) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fakeFetch(handler), SPEC.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_order", "get_product", "me", "quote_shipping"]);
});

test("quote_shipping sends skuinfo and the TVC token (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { Success: true, Currency: "USD", Shippings: [{ ShippingMethodCode: "EUDDP", ShippingMethod: "YunExpress", ShippingCost: 5.31, DeliveryCycle: "8-12 business days" }] } }; });
  const res = await client.callTool({ name: "quote_shipping", arguments: { product_id: "660402384A", country: "US", quantity: 1 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.options[0].id, "EUDDP");
  assert.deepEqual(JSON.parse(seen.init.body), { skuinfo: "660402384A*1", countrycode: "US" });
  assert.equal(seen.init.headers.Authorization, "TVC tok==");
});

test("unauthorized 200 body is an auth error (wire)", async () => {
  const client = await connect(() => ({ body: { Message: "unauthorized" } }));
  const res = await client.callTool({ name: "get_product", arguments: { id: "660166037C" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
});

test("get_product reads Detail (wire)", async () => {
  const client = await connect(() => ({ body: { Detail: { ItemNo: "660166037C", Name: "Case", Price: 1.5 } } }));
  const res = await client.callTool({ name: "get_product", arguments: { id: "660166037C" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.title, "Case");
  assert.equal(res.structuredContent.price, 1.5);
});
