import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/temu.json", import.meta.url), "utf8"));
const CREDS = { app_key: "f9d5cc9313893a20d5aa85c654e8f503", app_secret: "c7e0a1a63542be4de3cb5488f9fba8149e8fc290", access_token: "2nifvmpyymvypwmcms5ct4uqqudrwgpmzbcnmkt1jzjkuaf3x56iixym", region: "us" };

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", fakeFetch(handler), a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

function checkSign(init) {
  const body = JSON.parse(init.body); const sig = body.sign; delete body.sign;
  const parts = Object.keys(body).sort().map((k) => k + (typeof body[k] === "string" ? body[k] : JSON.stringify(body[k]))).join("");
  assert.equal(sig, crypto.createHash("md5").update(CREDS.app_secret + parts + CREDS.app_secret).digest("hex").toUpperCase());
  assert.equal(body.app_key, CREDS.app_key);
  assert.equal(body.data_type, "JSON");
  assert.equal(typeof body.timestamp, "number");
  return body;
}

test("temu: list_orders posts a body-signed router call", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { success: true, result: { totalItemNum: 1, pageItems: [{ parentOrderMap: { parentOrderSn: "PO-211-01", parentOrderStatus: 2 } }] } } }; });
  const res = await client.callTool({ name: "list_orders", arguments: { status: "unshipped", since: "2026-09-01" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.orders[0].id, "PO-211-01");
  assert.equal(seen.url.href, "https://openapi-b-us.temu.com/openapi/router");
  const body = checkSign(seen.init);
  assert.equal(body.type, "bg.order.list.v2.get");
  assert.equal(body.parentOrderStatus, 2);
  assert.equal(body.createAfter, 1788220800);
  assert.equal(body.createBefore, 4102444800);
});

test("temu: end_listing deletes by numeric goodsId", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { success: true, result: { success: true } } }; });
  const res = await client.callTool({ name: "end_listing", arguments: { listing_id: "601099548666279" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "deleted");
  const body = checkSign(seen.init);
  assert.equal(body.type, "temu.local.goods.delete");
  assert.equal(body.goodsId, 601099548666279);
});

test("temu: success false is an error result", async () => {
  const client = await connect(() => ({ body: { success: false, errorCode: 3000032, errorMsg: "access_token don't have this api access" } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
});
