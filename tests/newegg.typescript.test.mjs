import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/newegg.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => JSON.stringify(r.body ?? {}) }; };

Object.assign(process.env, {
  PLATFORM_MCP_NEWEGG_API_KEY: "720ddc067f4d115bd544aff46bc75634", PLATFORM_MCP_NEWEGG_SECRET_KEY: "21EC2020-3AEA", PLATFORM_MCP_NEWEGG_SELLER_ID: "A006",
  PLATFORM_MCP_NEWEGG_COUNTRY_CODE: "USA", PLATFORM_MCP_NEWEGG_CURRENCY: "USD", PLATFORM_MCP_NEWEGG_WAREHOUSE_LOCATION: "USA",
});

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("newegg: inventory body, key headers and sellerid (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { SellerID: "A006" } }; });
  const res = await client.callTool({ name: "set_inventory", arguments: { sku: "A006BSP3", quantity: 7 } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.pathname, "/marketplace/contentmgmt/item/international/inventory");
  assert.equal(seen.url.searchParams.get("sellerid"), "A006");
  assert.equal(seen.init.headers.Authorization, "720ddc067f4d115bd544aff46bc75634");
  assert.equal(seen.init.headers.SecretKey, "21EC2020-3AEA");
  assert.deepEqual(JSON.parse(seen.init.body), { Type: "1", Value: "A006BSP3", InventoryList: { Inventory: [{ WarehouseLocation: "USA", AvailableQuantity: "7" }] } });
});

test("newegg: list_orders maps OrderInfoList (wire)", async () => {
  const client = await connect(() => ({ body: { IsSuccess: true, ResponseBody: { PageInfo: { TotalCount: 1 }, OrderInfoList: [{ OrderNumber: 511952652, OrderStatusDescription: "Unshipped", OrderTotalAmount: 1.0, CurrencyCode: "USD" }] } } }));
  const res = await client.callTool({ name: "list_orders", arguments: {} });
  assert.equal(res.structuredContent.orders[0].id, "511952652");
  assert.equal(res.structuredContent.total, 1);
});
