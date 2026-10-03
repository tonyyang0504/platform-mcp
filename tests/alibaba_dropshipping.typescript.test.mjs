import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/alibaba_dropshipping.json", import.meta.url), "utf8"));
const CREDS = { app_key: "500123", app_secret: "ali-secret-0123456789", access_token: "50000601c30atpedfgu3LVvik87Ixlsvle3mSoB", ship_to_country: "US", currency: "USD" };

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", fakeFetch(handler), a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

function checkSign(url, apiPath) {
  const params = Object.fromEntries(url.searchParams); const sig = params.sign; delete params.sign;
  assert.equal(sig, crypto.createHmac("sha256", CREDS.app_secret).update(apiPath + Object.keys(params).sort().map((k) => k + params[k]).join("")).digest("hex").toUpperCase());
  assert.equal(params.sign_method, "sha256");
  return params;
}

test("alibaba_dropshipping: product description is signed over the API path without /rest", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { code: "0", result: { result_code: "200", result_data: { product_id: 1600398490, title: "Earbuds", currency: "USD", detail_url: "https://www.alibaba.com/x.html", main_image: "https://s01.alicdn.com/a.jpg", skus: [{ sku_id: 106117950042, cost_discount_price: "8.50" }] } } } }; });
  const res = await client.callTool({ name: "get_product", arguments: { id: "1600398490" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "1600398490");
  assert.equal(res.structuredContent.price, "8.50");
  assert.equal(seen.pathname, "/rest/eco/buyer/product/description");
  const p = checkSign(seen, "/eco/buyer/product/description");
  assert.deepEqual(JSON.parse(p.query_req), { product_id: 1600398490, ship_to_country: "US", currency: "USD" });
});

test("alibaba_dropshipping: create_order packs product_list and logistics_detail", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { code: "0", value: { trade_id: "12345321", pay_url: "https://pay.example/x" } } }; });
  const items = [{ product_id: 213421, quantity: "3" }];
  const addr = { address: "Washington Square", country: "United States of America", country_code: "US", contact_person: "Ann Lee" };
  const res = await client.callTool({ name: "create_order", arguments: { items, shipping_address: addr, shipping_option: "EX_ASP_Economy_Express_3C" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "12345321");
  assert.equal(seen.init.method, "POST");
  const p = checkSign(seen.url, "/buynow/order/create");
  assert.deepEqual(JSON.parse(p.product_list), items);
  assert.deepEqual(JSON.parse(p.logistics_detail), { carrier_code: "EX_ASP_Economy_Express_3C", shipment_address: addr });
});

test("alibaba_dropshipping: non-zero code is an error result", async () => {
  const client = await connect(() => ({ body: { type: "ISV", code: "IllegalAccessToken", message: "expired" } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
});
