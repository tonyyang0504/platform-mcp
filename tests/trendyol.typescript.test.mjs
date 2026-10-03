import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const ID = "trendyol";
const SPEC = JSON.parse(readFileSync(new URL(`../catalog/ecommerce_channels/${ID}.json`, import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const P = `PLATFORM_MCP_${ID.toUpperCase()}_`;
Object.assign(process.env, { [P + "API_KEY"]: "TYKEY123456", [P + "API_SECRET"]: "TYSECRET987654", [P + "SELLER_ID"]: "1234", [P + "USER_AGENT"]: "1234 - SelfIntegration", [P + "API_HOST"]: "apigw.trendyol.com" });

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test(`${ID}: stock update body, basic auth and User-Agent (wire)`, async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { batchRequestId: "fa75" } }; });
  const res = await client.callTool({ name: "set_inventory", arguments: { sku: "8680000000", quantity: 5 } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.href, "https://apigw.trendyol.com/integration/inventory/sellers/1234/products/price-and-inventory");
  assert.equal(seen.init.headers.Authorization, "Basic " + Buffer.from("TYKEY123456:TYSECRET987654").toString("base64"));
  assert.equal(seen.init.headers["User-Agent"], "1234 - SelfIntegration");
  assert.deepEqual(JSON.parse(seen.init.body), { items: [{ barcode: "8680000000", quantity: 5 }] });
});

test(`${ID}: list_orders maps packages (wire)`, async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { totalElements: 1, content: [{ orderNumber: "10654411111", status: "Created", packageTotalPrice: 498.9, currencyCode: "TRY" }] } }; });
  const res = await client.callTool({ name: "list_orders", arguments: { status: "Created" } });
  assert.equal(seen.searchParams.get("page"), "0");
  assert.equal(res.structuredContent.orders[0].id, "10654411111");
  assert.equal(res.structuredContent.total, 1);
});
