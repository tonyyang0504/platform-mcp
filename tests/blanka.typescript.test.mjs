import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/blanka.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_key: "key1" }, 50, "test", fakeFetch(handler), SPEC.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["create_order", "list_products", "me"]);
});

test("list_products reads results and count (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { count: 2, results: [{ id: 1, name: "Konjac Sponge", sku: "BLNK-KJS" }] } }; });
  const res = await client.callTool({ name: "list_products", arguments: { page: 2, limit: 1 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.products[0].id, "1");
  assert.equal(res.structuredContent.total, 2);
  assert.equal(seen.url.searchParams.get("page"), "2");
  assert.equal(seen.init.headers.Authorization, "key1");
});

test("create_order posts line_items (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 201, body: { id: "337539", status: "PAYMENT_REQUIRED" } }; });
  const res = await client.callTool({ name: "create_order", arguments: { items: [{ sku: "S1", quantity: 1 }], shipping_address: { first_name: "J", country: "US" } } });
  assert.equal(res.structuredContent.id, "337539");
  const body = JSON.parse(seen.init.body);
  assert.deepEqual(body.line_items, [{ sku: "S1", quantity: 1 }]);
  assert.equal(body.shipping_address.country, "US");
  assert.equal(typeof body.order_id, "string");
});
