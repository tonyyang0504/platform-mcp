import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/spreadconnect.json", import.meta.url), "utf8"));

async function connect(handler, creds = { access_token: "tok" }) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fakeFetch(handler), SPEC.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_order", "get_product", "list_products", "me", "track"]);
});

test("list_products sends limit/offset and X-SPOD-ACCESS-TOKEN (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { items: [{ id: 77, title: "Logo Tee", variants: [{ sku: "SKU-1", d2cPrice: 24.99 }], images: [{ imageUrl: "https://img.test/1.png" }] }], count: 30, limit: 10, offset: 10 } }; });
  const res = await client.callTool({ name: "list_products", arguments: { page: 2, limit: 10 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.products[0].sku, "SKU-1");
  assert.equal(res.structuredContent.products[0].price, 24.99);
  assert.equal(res.structuredContent.total, 30);
  assert.equal(seen.url.searchParams.get("offset"), "10");
  assert.equal(seen.init.headers["X-SPOD-ACCESS-TOKEN"], "tok");
});

test("track maps shipments to events (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: [{ id: 9, shipping: { type: { company: "DHL", name: "Standard" } }, tracking: [{ code: "JJD01", url: "https://dhl.test" }] }] }; });
  const res = await client.callTool({ name: "track", arguments: { order_id: "42" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.events[0].tracking_number, "JJD01");
  assert.equal(seen.pathname, "/orders/42/shipments");
});
