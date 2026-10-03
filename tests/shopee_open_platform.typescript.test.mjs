import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => ({ "content-type": "application/json" })[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/shopee_open_platform.json", import.meta.url), "utf8"));
const CREDS = { partner_id: "2001887", partner_key: "shpk-partner-key-0123", shop_id: "322300222", refresh_token: "4c72595349-one", host: "partner.shopeemobile.com" };
const mac = (s) => crypto.createHmac("sha256", CREDS.partner_key).update(s).digest("hex");

async function connect(handler) {
  const a = SPEC.adapter;
  const t = new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", fakeFetch(handler), a.envelope ?? {});
  const server = buildServer(SPEC, t);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return { client, t };
}

test("shopee: signed refresh (query sign + JSON body ints) then signed shop call with the minted token (wire)", async () => {
  const log = [];
  const { client, t } = await connect((url, init) => { log.push({ url, init });
    if (url.pathname === "/api/v2/auth/access_token/get") return { body: { error: "", access_token: "71594a4c5453-A1", refresh_token: "516c6b5777-two", expire_in: 14400 } };
    return { body: { error: "", response: { order_sn: "201214JAJXU6G7", logistics_status: "LOGISTICS_DELIVERY_DONE", tracking_info: [{ description: "Delivered" }] } } }; });
  const res = await client.callTool({ name: "track", arguments: { order_id: "201214JAJXU6G7" } });
  assert.equal(res.isError, false); assert.equal(res.structuredContent.status, "LOGISTICS_DELIVERY_DONE");
  const tq = log[0].url.searchParams;
  assert.equal(tq.get("sign"), mac("2001887/api/v2/auth/access_token/get" + tq.get("timestamp")));
  assert.deepEqual(JSON.parse(log[0].init.body), { refresh_token: "4c72595349-one", partner_id: 2001887, shop_id: 322300222 });
  assert.equal(t.creds.refresh_token, "516c6b5777-two");
  const q = log[1].url.searchParams;
  assert.equal(q.get("access_token"), "71594a4c5453-A1"); assert.equal(q.get("order_sn"), "201214JAJXU6G7");
  assert.equal(q.get("sign"), mac("2001887/api/v2/logistics/get_tracking_info" + q.get("timestamp") + "71594a4c5453-A1322300222"));
});

test("shopee: a non-empty error field is an isError result", async () => {
  const { client } = await connect((url) => url.pathname === "/api/v2/auth/access_token/get" ? { body: { error: "", access_token: "A", expire_in: 14400 } } : { body: { error: "error_param", message: "Wrong parameters" } });
  assert.equal((await client.callTool({ name: "get_product", arguments: { id: "1" } })).isError, true);
});
