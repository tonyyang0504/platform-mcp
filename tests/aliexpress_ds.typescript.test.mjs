import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/aliexpress_ds.json", import.meta.url), "utf8"));
const CREDS = { app_key: "500123", app_secret: "ae-secret-0123456789", access_token: "50000601c30atpedfgu3LVvik87", ship_to_country: "US", currency: "USD", language: "en_US" };

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", fakeFetch(handler), a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

function checkSign(url) {
  const params = Object.fromEntries(url.searchParams); const sig = params.sign; delete params.sign;
  const base = Object.keys(params).sort().map((k) => k + params[k]).join("");
  assert.equal(sig, crypto.createHmac("sha256", CREDS.app_secret).update(base).digest("hex").toUpperCase());
  return params;
}

test("aliexpress_ds: product.get is signed over the sorted parameters (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { code: "0", aliexpress_ds_product_get_response: { result: {
    ae_item_base_info_dto: { product_id: "4000903675543", subject: "Polarized Sunglasses", product_status_type: "onSelling" },
    ae_item_sku_info_dtos: [{ sku_attr: "73:175#Black Green", offer_sale_price: "3.94", currency_code: "USD", sku_available_stock: "57" }] } } } }; });
  const res = await client.callTool({ name: "get_product", arguments: { id: "4000903675543" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "4000903675543");
  assert.equal(res.structuredContent.title, "Polarized Sunglasses");
  assert.equal(res.structuredContent.sku, "73:175#Black Green");
  assert.equal(seen.pathname, "/sync");
  const p = checkSign(seen);
  assert.equal(p.method, "aliexpress.ds.product.get");
  assert.equal(p.product_id, "4000903675543");
  assert.equal(p.ship_to_country, "US");
  assert.equal(p.target_currency, "USD");
  assert.equal(p.sign_method, "sha256");
  assert.equal(p.access_token, CREDS.access_token);
});

test("aliexpress_ds: create_order packs items and address into the place-order DTO", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { code: "0", aliexpress_ds_order_create_response: { result: { is_success: "true", order_list: [8190001234] } } } }; });
  const items = [{ product_id: "1005005511268056", product_count: 1, sku_attr: "14:175#Black" }];
  const addr = { address: "1 Main St", city: "Austin", province: "Texas", country: "US", zip: "78701", full_name: "Ann Lee" };
  const res = await client.callTool({ name: "create_order", arguments: { items, shipping_address: addr } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "8190001234");
  assert.equal(seen.init.method, "POST");
  const p = checkSign(seen.url);
  assert.deepEqual(JSON.parse(p.param_place_order_request4_open_api_d_t_o), { logistics_address: addr, product_items: items });
});

test("aliexpress_ds: gateway error code is an auth error", async () => {
  const client = await connect(() => ({ body: { code: "IllegalAccessToken", type: "ISV", message: "The specified access token is invalid or expired", request_id: "r" } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
});
