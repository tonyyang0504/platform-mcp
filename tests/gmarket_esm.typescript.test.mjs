import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/gmarket_esm.json", import.meta.url), "utf8"));
const SECRET = "gm-secret-key-0123456789-abcdefghij";
const CREDS = { secret_key: SECRET, master_id: "master_1", site_seller_ids: "A:iacseller,G:gmkseller", site_type: "2" };

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

function checkJwt(init) {
  const token = hdr(init, "Authorization").split(" ")[1];
  const [h, p, s] = token.split(".");
  assert.equal(s, crypto.createHmac("sha256", SECRET).update(`${h}.${p}`).digest("base64url"));
  const header = JSON.parse(Buffer.from(h, "base64url").toString());
  const claims = JSON.parse(Buffer.from(p, "base64url").toString());
  assert.equal(header.kid, "master_1");
  assert.equal(header.alg, "HS256");
  assert.equal(claims.aud, "sa.esmplus.com");
  assert.equal(claims.sub, "sell");
  assert.equal(claims.ssi, "A:iacseller,G:gmkseller");
}

test("gmarket_esm: list_orders posts RequestOrders with a kid-bearing JWT", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { ResultCode: 0, Message: "", Data: { TotalCount: 1, RequestOrders: [{ OrderNo: 2946269058, OrderStatus: 1, AcntMoney: "25000", PayDate: "2019-04-10T17:45:50.507" }] } } }; });
  const res = await client.callTool({ name: "list_orders", arguments: { status: "paid", since: "2026-09-01" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.orders[0].id, "2946269058");
  assert.equal(seen.url.pathname, "/shipping/v1/Order/RequestOrders");
  const body = JSON.parse(seen.init.body);
  assert.equal(body.siteType, 2);
  assert.equal(body.orderStatus, 1);
  assert.equal(body.requestDateFrom, "2026-09-01");
  checkJwt(seen.init);
});

test("gmarket_esm: mark_shipped sends integer order and carrier codes", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { ResultCode: 0, Message: "Success", Data: { OrderNo: 2503423671 } } }; });
  const res = await client.callTool({ name: "mark_shipped", arguments: { order_id: "2503423671", carrier: "10013", tracking_number: "123456789012" } });
  assert.equal(res.isError, false);
  const body = JSON.parse(seen.init.body);
  assert.equal(body.OrderNo, 2503423671);
  assert.equal(body.DeliveryCompanyCode, 10013);
  assert.match(body.ShippingDate, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/);
  checkJwt(seen.init);
});

test("gmarket_esm: ResultCode 3000 is an error result", async () => {
  const client = await connect(() => ({ body: { ResultCode: 3000, Message: "31일 이하의 범위만 조회 할 수 있습니다.", Data: null } }));
  const res = await client.callTool({ name: "list_orders", arguments: { status: "paid", since: "2026-01-01" } });
  assert.equal(res.isError, true);
});
