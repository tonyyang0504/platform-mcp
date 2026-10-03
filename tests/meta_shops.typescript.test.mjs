import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/meta_shops.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => JSON.stringify(r.body ?? {}) }; };
Object.assign(process.env, { PLATFORM_MCP_META_SHOPS_ACCESS_TOKEN: "EAAG-system-user-token", PLATFORM_MCP_META_SHOPS_CATALOG_ID: "111", PLATFORM_MCP_META_SHOPS_CMS_ID: "222", PLATFORM_MCP_META_SHOPS_CURRENCY: "EUR" });

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("meta_shops: items_batch price string (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { handles: ["h1"] } }; });
  const res = await client.callTool({ name: "update_listing", arguments: { listing_id: "SKU-1", price: 12.5 } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.href, "https://graph.facebook.com/v25.0/111/items_batch");
  assert.deepEqual(JSON.parse(seen.init.body), { item_type: "PRODUCT_ITEM", requests: [{ method: "UPDATE", data: { id: "SKU-1", price: "12.5 EUR" } }] });
});
