import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/dhgate_open.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const OK = { code: "00000000", message: "OK" };

async function connect(handler) {
  const creds = { client_id: "APPKEY", client_secret: "APPSECRET", refresh_token: "REFRESH-1" };
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fakeFetch(handler), SPEC.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

const token = (url) => url.hostname === "secure.dhgate.com" ? { body: { access_token: "ACCESS-1", expires_in: "864000000", refresh_token: "REFRESH-2" } } : null;

test("tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["create_order", "get_order", "get_product", "list_products", "me", "quote_shipping"]);
});

test("get_product sends method, v, timestamp and access_token (wire)", async () => {
  const calls = [];
  const client = await connect((url, init) => { calls.push({ url, init }); return token(url) ?? { body: { status: OK, itemCode: "202325055", itemName: "FashionHat", currency: "USD", dhgateProductUrl: "https://www.dhgate.com/product/detail/202325055.html", itemSkuList: [{ minBuyerPrice: 4.5, inventory: 200, skuMD5: "abc" }], itemImgList: [{ imgUrl: "f2/x.jpg", mainImg: 0 }] } }; });
  const res = await client.callTool({ name: "get_product", arguments: { id: "202325055" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.title, "FashionHat");
  assert.equal(res.structuredContent.price, 4.5);
  assert.equal(res.structuredContent.stock, 200);
  const q = calls[1].url.searchParams;
  assert.equal(q.get("method"), "dh.dropshipping.item.get");
  assert.equal(q.get("itemCode"), "202325055");
  assert.equal(q.get("access_token"), "ACCESS-1");
  assert.match(q.get("timestamp"), /^\d{13}$/);
});

test("create_order posts cartList/contactInfo JSON strings (wire)", async () => {
  let seen;
  const client = await connect((url, init) => token(url) ?? (seen = { url, init }, { body: { status: OK, orderList: [{ orderInfo: { id: 985776655, orderTotal: 69.6 } }] } }));
  const items = [{ itemcode: 634706114, skuMd5: "562e", quantity: 5 }];
  const addr = { firstname: "zhao", lastname: "yiyi", country: "US", state: "CA", city: "Chicago", addressline1: "1 Main St", postalcode: "12345", tel: "1311" };
  const res = await client.callTool({ name: "create_order", arguments: { items, shipping_address: addr } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "985776655");
  assert.equal(seen.init.method, "POST");
  const form = new URLSearchParams(String(seen.init.body));
  assert.deepEqual(JSON.parse(form.get("cartList")), items);
  assert.deepEqual(JSON.parse(form.get("contactInfo")), addr);
});

test("router error in a 200 body is an error (wire)", async () => {
  const client = await connect((url) => token(url) ?? { body: { code: "23", message: "Invalid App Key", solution: "use the legal appKey" } });
  const res = await client.callTool({ name: "get_order", arguments: { id: "1330312162" } });
  assert.equal(res.isError, true);
});
