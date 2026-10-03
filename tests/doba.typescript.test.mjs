import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/doba.json", import.meta.url), "utf8"));
const { privateKey, publicKey } = crypto.generateKeyPairSync("rsa", { modulusLength: 2048 });
const der = privateKey.export({ type: "pkcs8", format: "der" }).toString("base64");
const CREDS = { app_key: "20201103773281123722592256", private_key: `-----BEGIN PRIVATE KEY-----\\n${der}\\n-----END PRIVATE KEY-----`, platform_id: "3" };

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", fakeFetch(handler), a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

const hdr = (init, name) => { const h = init.headers ?? {}; const k = Object.keys(h).find((x) => x.toLowerCase() === name.toLowerCase()); return k ? h[k] : undefined; };

function checkSign(init) {
  assert.equal(hdr(init, "appKey"), CREDS.app_key);
  assert.equal(hdr(init, "signType"), "rsa2");
  const ts = hdr(init, "timestamp");
  assert.match(ts, /^\d{13}$/);
  const ok = crypto.createVerify("RSA-SHA256").update(`appKey=${CREDS.app_key}&signType=rsa2&timestamp=${ts}`).verify(publicKey, hdr(init, "sign"), "base64");
  assert.equal(ok, true);
}

test("doba: get_product is signed with SHA256withRSA headers", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { responseCode: "000000", businessData: { data: [{ spuId: "ivUfpgDdAOoh", title: "Marker Boards", children: [{ currencyId: "USD", stocks: [{ itemNo: "D0102HEVPDA", availableNum: 100, sellingPrice: 150.32 }] }] }] } } }; });
  const res = await client.callTool({ name: "get_product", arguments: { id: "ivUfpgDdAOoh" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.sku, "D0102HEVPDA");
  assert.equal(seen.url.pathname, "/api/goods/doba/spu/detail");
  assert.equal(seen.url.searchParams.get("spuId"), "ivUfpgDdAOoh");
  checkSign(seen.init);
});

test("doba: create_order posts the importOrder JSON", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { responseCode: "000000", businessData: { data: { orderSuccessResList: [{ ordBusiId: 1017040801, totalPay: 111, currency: "USD" }] } } } }; });
  const addr = { name: "Ann Lee", addr1: "1 Main St", city: "New York", provinceCode: "NY", countryCode: "US", zip: "10041", telephone: "2125550100" };
  const items = [{ itemNo: "D0102HEVPDA", quantityOrdered: "2", shippingMethodId: "WAfpUKUWyPar" }];
  const res = await client.callTool({ name: "create_order", arguments: { items, shipping_address: addr } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "1017040801");
  assert.deepEqual(JSON.parse(seen.init.body), { billingAddress: addr, openApiImportDSOrderList: [{ orderNumber: "1", dsPlatformId: "3", shippingAddress: addr, goodsDetailDTOList: items }] });
  checkSign(seen.init);
});

test("doba: responseCode 999999 is an error result", async () => {
  const client = await connect(() => ({ body: { responseCode: "999999", responseMessage: "Operate Fail." } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
});
