import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/swag_pro_printfection.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler, creds = { api_key: "pf-secret" }) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["create_order", "get_order", "get_product", "list_products", "me", "track"]);
});

test("get_order maps manifest totals and basic auth (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { id: 1, status: "shipped", created_at: "2014-09-12T10:22:37Z", manifest: { total: 20, shipments: [{ carrier: "UPS", tracking_numbers: ["1Z"] }] } } }; });
  const res = await client.callTool({ name: "get_order", arguments: { id: "1" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "shipped");
  assert.equal(res.structuredContent.total, 20);
  assert.equal(res.structuredContent.tracking_number, "1Z");
  assert.equal(seen.url.pathname, "/v2/orders/1");
  assert.equal(seen.init.headers.Authorization, "Basic " + Buffer.from("pf-secret:").toString("base64"));
});

test("create_order sends campaign_id, ship_to and lineitems (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { id: 9, status: "open" } }; }, { api_key: "pf-secret", campaign_id: "2" });
  const res = await client.callTool({ name: "create_order", arguments: { items: [{ item_id: 1, size_id: 0, quantity: 1 }], shipping_address: { name: "J" } } });
  assert.equal(res.isError, false);
  assert.deepEqual(JSON.parse(seen.init.body), { campaign_id: 2, ship_to: { name: "J" }, lineitems: [{ item_id: 1, size_id: 0, quantity: 1 }] });
});

test("server error is an isError result (wire)", async () => {
  const client = await connect(() => ({ status: 500, body: { error: "boom" } }));
  const res = await client.callTool({ name: "get_product", arguments: { id: "1" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "upstream_error");
});
