import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/best_buy_ca.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (r.status === 204 ? "" : JSON.stringify(r.body ?? {})) }; };

process.env.PLATFORM_MCP_BEST_BUY_CA_API_KEY = "SHOPKEY-0123456789abcdef";
process.env.PLATFORM_MCP_BEST_BUY_CA_INSTANCE_HOST = "marketplace.bestbuy.ca";
delete process.env.PLATFORM_MCP_BEST_BUY_CA_SHOP_ID;

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("best_buy_ca: raw Authorization key on the configured instance host (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { shop_id: 2001, shop_name: "Acme" } }; });
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["list_orders", "mark_shipped", "me"]);
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, false);
  assert.equal(seen.url.href, "https://marketplace.bestbuy.ca/api/account");
  assert.equal(seen.init.headers.Authorization, "SHOPKEY-0123456789abcdef");
});

test("best_buy_ca: list_orders maps OR11 (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { total_count: 1, orders: [{ order_id: "ORD-1-A", order_state: "SHIPPING", total_price: 59.9, currency_iso_code: "EUR", created_date: "2026-09-20T10:00:00Z" }] } }; });
  const res = await client.callTool({ name: "list_orders", arguments: { status: "SHIPPING", limit: 5 } });
  assert.equal(res.isError, false);
  assert.equal(seen.pathname, "/api/orders");
  assert.equal(seen.searchParams.get("order_state_codes"), "SHIPPING");
  assert.equal(seen.searchParams.get("max"), "5");
  assert.equal(res.structuredContent.orders[0].id, "ORD-1-A");
  assert.equal(res.structuredContent.total, 1);
});

test("best_buy_ca: mark_shipped sends OR23 tracking body (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 204 }; });
  const res = await client.callTool({ name: "mark_shipped", arguments: { order_id: "ORD-1-A", carrier: "UPS", tracking_number: "1Z999" } });
  assert.equal(res.isError, false);
  assert.equal(seen.init.method, "PUT");
  assert.equal(seen.url.pathname, "/api/orders/ORD-1-A/tracking");
  assert.deepEqual(JSON.parse(seen.init.body), { carrier_code: "UPS", tracking_number: "1Z999" });
  assert.equal(res.structuredContent.status, "tracking_updated");
});
