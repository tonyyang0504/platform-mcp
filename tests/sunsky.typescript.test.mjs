import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const ID = "sunsky";
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? { "content-type": "application/json" })[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL(`../catalog/ecommerce_suppliers/${ID}.json`, import.meta.url), "utf8"));
const CREDS = { key: "MYKEY", secret: "MYSECRET-sunsky-01", language: "en" };

async function connect(handler, spec = SPEC, creds = CREDS) {
  const a = spec.adapter;
  const server = buildServer(spec, new Transport(a.base_url, a.auth, { ...creds }, 50, "test", fakeFetch(handler), a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

function checkSign(url, secret = CREDS.secret) {
  const p = Object.fromEntries(url.searchParams); const sig = p.signature; delete p.signature;
  assert.equal(sig, crypto.createHash("md5").update(Object.keys(p).sort().map((k) => p[k]).join("") + "@" + secret).digest("hex"));
  return p;
}

test(`${ID}: the convention's own signature example (wire)`, async () => {
  const spec = JSON.parse(JSON.stringify(SPEC));
  spec.adapter.tools.me.fixed_params = { name: "John Smith", age: "19", gendar: "mail" };
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { result: "success", data: "5.2600" } }; }, spec, { key: "MYKEY", secret: "MYSECRET" });
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, false);
  assert.equal(seen.init.method, "POST");
  assert.equal(seen.url.searchParams.get("signature"), crypto.createHash("md5").update("19mailMYKEYJohn Smith@MYSECRET").digest("hex"));
});

test(`${ID}: product detail and create_order are signed over sorted values`, async () => {
  const seen = [];
  const client = await connect((url) => { seen.push(url); return url.pathname.endsWith("detail.do")
    ? { body: { result: "success", data: { id: 3889036, itemNo: "EDA008394601A", name: "LED badge", price: "2.79", stock: 7 } } }
    : { body: { result: "success", data: { number: "2301144841", status: 1, totalAmount: "18.33" } } }; });
  const p = await client.callTool({ name: "get_product", arguments: { id: "EDA008394601A" } });
  assert.equal(p.structuredContent.id, "EDA008394601A"); assert.equal(p.structuredContent.stock, 7);
  assert.deepEqual(checkSign(seen[0]), { key: "MYKEY", itemNo: "EDA008394601A", lang: "en" });
  const o = await client.callTool({ name: "create_order", arguments: { items: [{ itemNo: "A1", qty: 2 }, { itemNo: "B2", qty: 1 }], shipping_address: { countryId: 41, city: "Austin", receiver: "Ann Lee", shipment: "drop" }, shipping_option: "278" } });
  assert.equal(o.isError, false); assert.equal(o.structuredContent.id, "2301144841");
  const q = checkSign(seen[1]);
  assert.equal(q["items.2.itemNo"], "B2"); assert.equal(q["items.1.qty"], "2"); assert.equal(q["deliveryAddress.countryId"], "41"); assert.equal(q["deliveryAddress.shippingWayId"], "278");
});

test(`${ID}: result error envelope is an isError result`, async () => {
  const client = await connect(() => ({ body: { result: "error", messages: ["NO_PERMISSION_DUE_TO_SIGNATURE"] } }));
  const res = await client.callTool({ name: "get_order", arguments: { id: "1" } });
  assert.equal(res.isError, true);
  assert.ok(!JSON.stringify(res.structuredContent).includes(CREDS.secret));
});
