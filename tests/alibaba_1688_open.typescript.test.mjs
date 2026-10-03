import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/alibaba_1688_open.json", import.meta.url), "utf8"));
const CREDS = { client_id: "1000000", client_secret: "test123", refresh_token: "479f9564-1049-456e-ab62-29d3e82277d9", language: "en", order_flow: "saleproxy" };

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
  const params = Object.fromEntries(url.searchParams); const sig = params._aop_signature; delete params._aop_signature;
  const s = url.pathname.slice("/openapi/".length) + Object.keys(params).sort().map((k) => k + params[k]).join("");
  assert.equal(sig, crypto.createHmac("sha1", CREDS.client_secret).update(s).digest("hex").toUpperCase());
  assert.equal(params.access_token, "f14da3b8-b0b1-4f73-a5de-9bed637e0188");
  return params;
}

test("alibaba_1688_open: documented signature example", () => {
  assert.equal(crypto.createHmac("sha1", "test123").update("param2/1/system/currentTime/1000000a1b2").digest("hex").toUpperCase(), "33E54F4F7B989E3E0E912D3FBD2F1A03CA7CCE88");
});

test("alibaba_1688_open: refresh token then signed keyword search", async () => {
  const calls = [];
  const client = await connect((url, init) => {
    calls.push({ url, init });
    if (url.pathname.includes("system.oauth2/getToken")) return { body: { access_token: "f14da3b8-b0b1-4f73-a5de-9bed637e0188", expires_in: "36000" } };
    return { body: { result: { success: true, result: { totalRecords: 1, data: [{ offerId: 620201390233, subjectTrans: "Biscuits", priceInfo: { price: "10" } }] } } } };
  });
  const res = await client.callTool({ name: "list_products", arguments: { query: "biscuits" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.products[0].id, "620201390233");
  assert.equal(calls[0].url.pathname, "/openapi/http/1/system.oauth2/getToken/1000000");
  const form = Object.fromEntries(new URLSearchParams(String(calls[0].init.body)));
  assert.equal(form.grant_type, "refresh_token");
  assert.equal(form.client_id, "1000000");
  assert.equal(calls[1].url.pathname, "/openapi/param2/1/com.alibaba.fenxiao.crossborder/product.search.keywordQuery/1000000");
  const p = checkSign(calls[1].url);
  assert.equal(JSON.parse(p.offerQueryParam).keyword, "biscuits");
});

test("alibaba_1688_open: gateway error_code is an error result", async () => {
  const client = await connect((url) => url.pathname.includes("getToken")
    ? { body: { access_token: "f14da3b8-b0b1-4f73-a5de-9bed637e0188", expires_in: "36000" } }
    : { body: { error_code: "gw.QosAppFrequencyLimit", error_message: "App call exceeds limited frequency" } });
  const res = await client.callTool({ name: "get_order", arguments: { id: "58218860983545941" } });
  assert.equal(res.isError, true);
});
