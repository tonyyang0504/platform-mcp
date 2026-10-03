import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/mercari_shops_jp.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => JSON.stringify(r.body ?? {}) }; };

process.env.PLATFORM_MCP_MERCARI_SHOPS_JP_ACCESS_TOKEN = "PAT-secret-0123456789";
process.env.PLATFORM_MCP_MERCARI_SHOPS_JP_API_HOST = "api.mercari-shops.com";
process.env.PLATFORM_MCP_MERCARI_SHOPS_JP_USER_AGENT = "EXAMPLE_SHOP/1.0.0";

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("mercari_shops_jp: set_inventory mutation by skuCode (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { data: { updateProductVariant: { productVariant: { id: "v1", skuCode: "SKU-1", stockQuantity: 3 } } } } }; });
  const res = await client.callTool({ name: "set_inventory", arguments: { sku: "SKU-1", quantity: 3 } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.href, "https://api.mercari-shops.com/v1/graphql");
  assert.equal(seen.init.headers.Authorization, "Bearer PAT-secret-0123456789");
  assert.deepEqual(JSON.parse(seen.init.body).variables, { by: { skuCode: "SKU-1" }, input: { stockQuantity: 3 } });
});

test("mercari_shops_jp: GraphQL errors are errors (wire)", async () => {
  const client = await connect(() => ({ body: { errors: [{ message: "forbidden" }], data: null } }));
  const res = await client.callTool({ name: "end_listing", arguments: { listing_id: "p1" } });
  assert.equal(res.isError, true);
});
