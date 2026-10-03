import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/nova_engel.json", import.meta.url), "utf8"));
const CREDS = { user: "shop-user", password: "PASSWORD-nova-1", language: "es" };
const jsonResp = (status, body) => ({ status, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null) }, text: async () => JSON.stringify(body) });

async function connect(log, handler) {
  const a = SPEC.adapter;
  const f = async (url, init) => { log.push({ url, init }); return url.endsWith("/api/login") ? jsonResp(200, { Token: "TOKEN-ne-1" }) : handler(url, init); };
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", f, a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("nova_engel: login token travels in the product paging path (wire)", async () => {
  const log = [];
  const c = await connect(log, () => jsonResp(200, [{ Id: 1234, EANs: ["8411061000000"], Description: "EDT 100 ml", Price: 21.5, Stock: 12 }]));
  const res = await c.callTool({ name: "list_products", arguments: { page: 2, limit: 20 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.products[0].id, "1234");
  assert.deepEqual(JSON.parse(log[0].init.body), { User: "shop-user", Password: "PASSWORD-nova-1" });
  assert.equal(log[1].url, "https://drop.novaengel.com/api/products/paging/TOKEN-ne-1/2/20/es");
  assert.equal(log[1].init.headers.Authorization, undefined);
});

test("nova_engel: sendv2 order array and order lookup", async () => {
  const log = [];
  const c = await connect(log, (url) => url.includes("/sendv2/") ? jsonResp(200, [{ BookingCode: "BK-9", Errors: [], Message: "OK", OrderNumber: "PO-77" }])
    : jsonResp(200, { OrderNumber: "PO-77", Total: 55.3, Status: 4, SendInfo: { Tracking: "1Z999", Carrier: "GLS" } }));
  const res = await c.callTool({ name: "create_order", arguments: { items: [{ product_id: "1234", quantity: 2 }], shipping_address: { order_number: "PO-77", name: "Ana", postal_code: "28013", country: "ES" } } });
  assert.equal(res.structuredContent.id, "PO-77");
  const sent = log.find((l) => l.url.endsWith("/api/orders/sendv2/TOKEN-ne-1"));
  assert.deepEqual(JSON.parse(sent.init.body), [{ OrderNumber: "PO-77", Name: "Ana", PostalCode: "28013", Country: "ES", Lines: [{ ProductId: 1234, Units: 2 }] }]);
  const t = await c.callTool({ name: "track", arguments: { order_id: "PO-77" } });
  assert.equal(t.structuredContent.events[0].tracking_number, "1Z999"); // auth audit: events array per the vocabulary
  assert.ok(log.some((l) => l.url === "https://drop.novaengel.com/api/orders/orderbyid/TOKEN-ne-1/PO-77"));
});
