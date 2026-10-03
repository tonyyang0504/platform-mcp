import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/takealot.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => JSON.stringify(r.body ?? {}) }; };

process.env.PLATFORM_MCP_TAKEALOT_AUTHORIZATION = "Key TAKEALOT-secret-key-123";
process.env.PLATFORM_MCP_TAKEALOT_MERCHANT_WAREHOUSE_ID = "4521";

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("takealot: set_inventory PATCHes SKU identifier with leadtime stock (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { offer: { offer_id: 1, status: "Buyable" } } }; });
  const res = await client.callTool({ name: "set_inventory", arguments: { sku: "DF22", quantity: 9 } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.href, "https://seller-api.takealot.com/v2/offers/offer/SKUDF22");
  assert.equal(seen.init.method, "PATCH");
  assert.equal(seen.init.headers.Authorization, "Key TAKEALOT-secret-key-123");
  assert.deepEqual(JSON.parse(seen.init.body), { leadtime_stock: [{ merchant_warehouse_id: 4521, quantity: 9 }] });
});
