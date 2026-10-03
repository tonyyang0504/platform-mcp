import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/shopee.json", import.meta.url), "utf8"));
const CREDS = { partner_id: "1001", shop_id: "600000", partner_key: "PKEY-shopee-0123456789", refresh_token: "REFRESH-sp-1" };
const mac = (s) => crypto.createHmac("sha256", CREDS.partner_key).update(s).digest("hex");

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", fakeFetch(handler), a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("shopee: signed refresh (JSON body with integer ids) then signed order list", async () => {
  const calls = [];
  const client = await connect((url, init) => {
    calls.push({ url, init });
    if (url.pathname === "/api/v2/auth/access_token/get") return { body: { error: "", access_token: "ACCESS-sp", refresh_token: "REFRESH-sp-2", expire_in: 14400 } };
    return { body: { error: "", message: "", response: { more: false, next_cursor: "", order_list: [{ order_sn: "201218V2Y6E59M", order_status: "SHIPPED" }] } } };
  });
  const res = await client.callTool({ name: "list_orders", arguments: { since: "2026-09-20" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.orders[0].id, "201218V2Y6E59M");
  assert.equal(calls[0].url.host, "partner.shopeemobile.com");
  assert.deepEqual(JSON.parse(calls[0].init.body), { refresh_token: "REFRESH-sp-1", partner_id: 1001, shop_id: 600000 });
  const tq = calls[0].url.searchParams;
  assert.equal(tq.get("sign"), mac(`1001/api/v2/auth/access_token/get${tq.get("timestamp")}`));
  const q = calls[1].url.searchParams;
  assert.equal(q.get("access_token"), "ACCESS-sp");
  assert.equal(q.get("sign"), mac(`1001/api/v2/order/get_order_list${q.get("timestamp")}ACCESS-sp600000`));
});

test("shopee: error field is an error result", async () => {
  const client = await connect((url) => url.pathname === "/api/v2/auth/access_token/get"
    ? { body: { error: "", access_token: "ACCESS-sp", refresh_token: "REFRESH-sp-2", expire_in: 14400 } }
    : { body: { error: "error_auth", message: "Invalid access_token." } });
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
});
