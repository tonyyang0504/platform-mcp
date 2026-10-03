import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/customcat.json", import.meta.url), "utf8"));

async function connect(handler, creds = { api_key: "k" }) {
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
  assert.deepEqual(tools.map((t) => t.name).sort(), ["create_order", "get_order", "list_products", "me", "track"]);
});

test("create_order posts to /order/{uuid} with flattened shipping fields (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { ORDER_ID: "x", MSG: "Order added successfully", CUSTOMCAT_ORDER_ID: "184DEF43" } }; }, { api_key: "k", sandbox: "1" });
  const res = await client.callTool({ name: "create_order", arguments: { items: [{ sku: "22-115-4774-254", quantity: 1 }], shipping_address: { first_name: "Joe", zip: "48216", country: "US" }, shipping_option: "Economy" } });
  assert.equal(res.isError, false);
  assert.match(seen.url.pathname, /^\/api\/v1\/order\/[0-9a-f-]{36}$/);
  assert.equal(seen.url.searchParams.get("api_key"), "k");
  const body = JSON.parse(seen.init.body);
  assert.equal(body.shipping_first_name, "Joe");
  assert.equal(body.shipping_method, "Economy");
  assert.equal(body.sandbox, "1");
});

test("get_order maps the status record (wire)", async () => {
  const client = await connect(() => ({ body: { ORDER_ID: "TestOrder1", ORDER_STATUS: "Shipped", ORDER_TOTAL: 19.47, ORDER_DATE: "March, 27 2018 12:14:45", SHIPMENTS: [{ TRACKING_ID: "9274890", VENDOR: "UPS" }] } }));
  const res = await client.callTool({ name: "get_order", arguments: { id: "TestOrder1" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.total, 19.47);
  assert.equal(res.structuredContent.tracking_number, "9274890");
});
