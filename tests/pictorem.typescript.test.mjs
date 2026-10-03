import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => ({ "content-type": "application/json" })[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/pictorem.json", import.meta.url), "utf8"));
const CREDS = { artflow_key: "AFK-test-0123456789" };

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", fakeFetch(handler), a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("pictorem: sendorder is multipart/form-data with bracketed fields and the ArtFlowKey header (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { status: true, msg: [], orderid: 472175 } }; });
  const res = await client.callTool({ name: "create_order", arguments: {
    items: [{ code: "1|canvas|stretched|horizontal|16|12", fileurl: "https://img.example.com/a.jpg", filetype: "jpg" }],
    shipping_address: { firstname: "Kathleen", lastname: "Bernal", address1: "3371 Sycamore Lake Road", city: "Oshkosh", province: "WI", country: "USA", cp: "54901" } } });
  assert.equal(res.isError, false); assert.equal(res.structuredContent.id, "472175");
  assert.equal(seen.url.href, "https://www.pictorem.com/artflow/0.1/sendorder/");
  assert.ok(seen.init.body instanceof FormData);
  assert.equal(seen.init.body.get("orderList[0][code]"), "1|canvas|stretched|horizontal|16|12");
  assert.equal(seen.init.body.get("deliveryInfo[cp]"), "54901");
  assert.equal(seen.init.body.get("orderList[1][code]"), null);
  assert.equal(seen.init.headers.ArtFlowKey, CREDS.artflow_key);
  assert.ok(!Object.keys(seen.init.headers).some((h) => h.toLowerCase() === "content-type"));
});

test("pictorem: order status and status=false errors", async () => {
  let n = 0;
  const client = await connect(() => (++n === 1 ? { body: { status: true, order: { orderid: 472174, order_status_label: "Shipped", tracking_number: "1Z9", tracking_carrier: "UPS" } } } : { body: { status: false, msg: { error: ["Order not found."] } } }));
  const t = await client.callTool({ name: "track", arguments: { order_id: "472174" } });
  assert.equal(t.structuredContent.tracking_number, "1Z9");
  assert.equal((await client.callTool({ name: "get_order", arguments: { id: "9" } })).isError, true);
});
