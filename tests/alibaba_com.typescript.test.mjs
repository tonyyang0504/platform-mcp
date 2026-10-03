import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/alibaba_com.json", import.meta.url), "utf8"));
const CREDS = { app_key: "12345678", app_secret: "helloworld", access_token: "50000601c30atpedfgu3LVvik87Ixlsvle3mSoB7701ceb156fPunYZ43GBg" };

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
  return params;
}

test("alibaba_com: seller order list is signed without the /rest prefix", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { code: "0", value: { total_count: "1", order_list: [{ trade_id: "271207727001028893", trade_status: "undeliver" }] } } }; });
  const res = await client.callTool({ name: "list_orders", arguments: { status: "undeliver" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.orders[0].id, "271207727001028893");
  assert.equal(seen.pathname, "/rest/alibaba/order/list");
  const p = checkSign(seen, "/alibaba/order/list");
  assert.equal(p.role, "seller");
});

test("alibaba_com: end_listing takes the product offline", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { code: "0", success: true } }; });
  const res = await client.callTool({ name: "end_listing", arguments: { listing_id: "1601314875038" } });
  assert.equal(res.isError, false);
  const p = checkSign(seen, "/alibaba/icbu/product/batch/update/status");
  assert.deepEqual(JSON.parse(p.product_id_list), [1601314875038]);
  assert.equal(p.action, "offline");
});

test("alibaba_com: IllegalAccessToken is an error result", async () => {
  const client = await connect(() => ({ body: { type: "ISV", code: "IllegalAccessToken", message: "The specified access token is invalid or expired" } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
});
