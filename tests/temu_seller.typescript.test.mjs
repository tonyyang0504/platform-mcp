import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => ({ "content-type": "application/json" })[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/temu_seller.json", import.meta.url), "utf8"));
const CREDS = { app_key: "f9d5cc9313893a20d5aa85c654e8f503", app_secret: "c7e0a1a63542be4de3cb5488f9fba8149e8fc290", access_token: "2nifvmpyymvypwmcms5ct4uq", region: "eu" };

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", fakeFetch(handler), a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("temu_seller: body-field MD5 signature over sorted body params (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { success: true, result: { total: 1, goodsList: [{ goodsId: 601099548666279, goodsName: "Desk lamp", retailPrice: { amount: "19.99", currency: "EUR" } }] } } }; });
  const res = await client.callTool({ name: "list_products", arguments: { query: "lamp", category: "12345", limit: 20 } });
  assert.equal(res.isError, false); assert.equal(res.structuredContent.products[0].id, "601099548666279");
  assert.equal(seen.url.href, "https://openapi-b-eu.temu.com/openapi/router");
  const body = JSON.parse(seen.init.body); const sig = body.sign; delete body.sign;
  const kv = Object.keys(body).sort().map((k) => k + (typeof body[k] === "string" ? body[k] : JSON.stringify(body[k]))).join("");
  assert.equal(sig, crypto.createHash("md5").update(CREDS.app_secret + kv + CREDS.app_secret).digest("hex").toUpperCase());
  assert.equal(body.type, "bg.local.goods.list.query"); assert.deepEqual(body.catIdList, [12345]); assert.equal(body.access_token, CREDS.access_token);
});

test("temu_seller: success=false is an isError result", async () => {
  const client = await connect(() => ({ body: { success: false, errorCode: 7000015, errorMsg: "sign is invalid" } }));
  assert.equal((await client.callTool({ name: "get_order", arguments: { id: "PO-1" } })).isError, true);
});
