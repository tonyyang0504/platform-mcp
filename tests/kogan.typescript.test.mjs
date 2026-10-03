import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/kogan.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => JSON.stringify(r.body ?? {}) }; };

process.env.PLATFORM_MCP_KOGAN_SELLER_TOKEN = "TOKEN-abcdef123456";
process.env.PLATFORM_MCP_KOGAN_SELLER_ID = "acme";
process.env.PLATFORM_MCP_KOGAN_API_HOST = "nimda.kogan.com";

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("kogan: seller headers and top-level array stock body (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { status: "AsyncResponsePending", pending_url: "https://nimda.kogan.com/api/marketplace/v2/task/t1/" } }; });
  const res = await client.callTool({ name: "set_inventory", arguments: { sku: "SKU1", quantity: 5 } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.href, "https://nimda.kogan.com/api/marketplace/v2/products/stockprice/");
  assert.equal(seen.init.headers.SellerToken, "TOKEN-abcdef123456");
  assert.equal(seen.init.headers.SellerID, "acme");
  assert.deepEqual(JSON.parse(seen.init.body), [{ product_sku: "SKU1", stock: 5 }]);
});

test("kogan: list_orders maps body rows (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { status: "Complete", body: [{ ID: "K-100", OrderStatus: "Shipped", TotalPrice: 10.5, Currency: "NZD" }] } }; });
  const res = await client.callTool({ name: "list_orders", arguments: { status: "Shipped" } });
  assert.equal(seen.searchParams.get("status"), "Shipped");
  assert.equal(res.structuredContent.orders[0].id, "K-100");
  assert.equal(res.structuredContent.orders[0].currency, "NZD");
});
