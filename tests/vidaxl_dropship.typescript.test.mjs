import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/vidaxl_dropship.json", import.meta.url), "utf8"));

async function connect(handler, creds = { email: "shop@example.com", api_token: "tok" }) {
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
  assert.deepEqual(tools.map((t) => t.name).sort(), ["create_order", "get_order", "get_product", "list_products", "me"]);
});

test("list_products uses Basic auth and limit/offset (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: [{ id: 4, name: "Cat Tree", code: "100058", price: "75.00", quantity: "0.0" }] }; });
  const res = await client.callTool({ name: "list_products", arguments: { page: 3, limit: 50 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.products[0].id, "100058");
  assert.equal(seen.url.searchParams.get("offset"), "100");
  assert.equal(seen.init.headers.Authorization, "Basic " + Buffer.from("shop@example.com:tok").toString("base64"));
});

test("get_order reads the nested order (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: [{ order: { id: "B2B111", status_order_name: "Sent", shipping_tracking: "TEST9999" } }] }; });
  const res = await client.callTool({ name: "get_order", arguments: { id: "B2B111" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "Sent");
  assert.equal(res.structuredContent.tracking_number, "TEST9999");
  assert.equal(seen.searchParams.get("id_eq"), "B2B111");
});
