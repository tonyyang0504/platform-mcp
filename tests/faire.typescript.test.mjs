import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/faire.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => JSON.stringify(r.body ?? {}) }; };
process.env.PLATFORM_MCP_FAIRE_ACCESS_TOKEN = "oat_4f9c2d7e81b3";
process.env.PLATFORM_MCP_FAIRE_APP_CREDENTIALS = "YXBhXzEyMzpzZWNyZXQ=";

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("faire: set inventory by SKU with both OAuth headers (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { inventories: {} } }; });
  const res = await client.callTool({ name: "set_inventory", arguments: { sku: "vanilla-2019", quantity: 7 } });
  assert.equal(res.isError, false);
  assert.equal(seen.init.method, "PATCH");
  assert.equal(seen.url.href, "https://www.faire.com/external-api/v2/product-inventory/by-skus");
  assert.equal(seen.init.headers["X-FAIRE-OAUTH-ACCESS-TOKEN"], "oat_4f9c2d7e81b3");
  assert.equal(seen.init.headers["X-FAIRE-APP-CREDENTIALS"], "YXBhXzEyMzpzZWNyZXQ=");
  assert.deepEqual(JSON.parse(seen.init.body), { inventories: [{ sku: "vanilla-2019", on_hand_quantity: 7 }] });
});

test("faire: orders cursor pagination", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { orders: [{ id: "bo_1", state: "NEW" }], cursor: "c_next" } }; });
  const res = await client.callTool({ name: "list_orders", arguments: { cursor: "c_1" } });
  assert.equal(res.structuredContent.next_cursor, "c_next");
  assert.equal(res.structuredContent.orders[0].status, "NEW");
  assert.equal(seen.searchParams.get("cursor"), "c_1");
});
