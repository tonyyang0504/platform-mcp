import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/kaufland.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => (r.status === 204 ? "" : JSON.stringify(r.body ?? {})) }; };

process.env.PLATFORM_MCP_KAUFLAND_CLIENT_KEY = "ck";
process.env.PLATFORM_MCP_KAUFLAND_SECRET_KEY = "sec";
process.env.PLATFORM_MCP_KAUFLAND_STOREFRONT = "de";

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("kaufland: set_inventory PATCH is signed over method, URI, body, timestamp (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { data: { id_unit: 3001, status: "AVAILABLE" } } }; });
  const res = await client.callTool({ name: "set_inventory", arguments: { listing_id: "3001", quantity: 12 } });
  assert.equal(res.isError, false);
  const h = seen.init.headers;
  assert.equal(seen.init.method, "PATCH");
  assert.equal(seen.url.searchParams.get("storefront"), "de");
  assert.equal(h["Shop-Signature"], crypto.createHmac("sha256", "sec").update(`PATCH\n${seen.url.toString()}\n${seen.init.body}\n${h["Shop-Timestamp"]}`).digest("hex"));
});

test("kaufland: list_orders maps order units (wire)", async () => {
  const client = await connect(() => ({ body: { data: [{ id_order_unit: 9001, id_order: "MMXX1", status: "sent", currency: "EUR" }], pagination: { total: 1 } } }));
  const res = await client.callTool({ name: "list_orders", arguments: {} });
  assert.equal(res.structuredContent.orders[0].id, "9001");
  assert.equal(res.structuredContent.total, 1);
});

test("kaufland: mark_shipped 204 (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 204 }; });
  const res = await client.callTool({ name: "mark_shipped", arguments: { order_id: "9001", carrier: "DHL", tracking_number: "0034" } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.pathname, "/v2/order-units/9001/send");
  assert.deepEqual(JSON.parse(seen.init.body), { tracking_numbers: "0034", carrier_code: "DHL" });
});
