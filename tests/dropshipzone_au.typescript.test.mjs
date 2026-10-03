import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/dropshipzone_au.json", import.meta.url), "utf8"));

async function connect(handler, creds = { email: "api@example.com", password: "pw" }) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fakeFetch(handler), SPEC.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("logs in, sends jwt token, maps products (wire)", async () => {
  const calls = [];
  const client = await connect((url, init) => {
    calls.push({ url, init });
    if (url.pathname === "/auth") return { body: { iat: 1, exp: 2, token: "T0K" } };
    return { body: { result: [{ sku: "V201-W12898984", title: "Car Fan Heater", price: 29.31, currency: "AUD", stock_qty: 44, gallery: ["https://cdn.test/0.png"] }], total: 91 } };
  });
  const res = await client.callTool({ name: "list_products", arguments: { query: "heater" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.products[0].id, "V201-W12898984");
  assert.equal(res.structuredContent.products[0].stock, 44);
  assert.deepEqual(JSON.parse(calls[0].init.body), { email: "api@example.com", password: "pw" });
  const last = calls.at(-1);
  assert.equal(last.init.headers.Authorization, "jwt T0K");
  assert.equal(last.url.searchParams.get("keywords"), "heater");
  assert.equal(last.url.searchParams.get("limit"), "40");
});

test("create_order flattens the consignee fields (wire)", async () => {
  let body;
  const client = await connect((url, init) => {
    if (url.pathname === "/auth") return { body: { token: "T0K" } };
    body = JSON.parse(init.body);
    return { body: [{ status: 1, serial_number: "P02100689" }] };
  });
  const res = await client.callTool({ name: "create_order", arguments: { items: [{ sku: "MOC-09M-2P-BK", qty: 3 }], shipping_address: { first_name: "John", last_name: "Baker", suburb: "Eugowra", postcode: "2806" } } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "P02100689");
  assert.equal(body.first_name, "John");
  assert.equal(body.postcode, "2806");
  assert.equal(body.your_order_no.length, 36);
  assert.deepEqual(body.order_items, [{ sku: "MOC-09M-2P-BK", qty: 3 }]);
});

test("track reads data.0.shipment (wire)", async () => {
  const client = await connect((url) => url.pathname === "/auth" ? { body: { token: "T0K" } } : { body: { status: 1, data: [{ increment_id: "100000001", shipment: [{ track_number: "1232132121", title: "Aus Post" }] }] } });
  const res = await client.callTool({ name: "track", arguments: { order_id: "100000001" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.events[0].carrier, "Aus Post");
});
