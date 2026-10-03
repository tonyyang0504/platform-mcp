import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/emag.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => JSON.stringify(r.body ?? {}) }; };

process.env.PLATFORM_MCP_EMAG_USERNAME = "api-user@shop.ro";
process.env.PLATFORM_MCP_EMAG_PASSWORD = "PASSWORDsecret1";
process.env.PLATFORM_MCP_EMAG_API_HOST = "marketplace-api.emag.bg";

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("emag: basic auth on the configured host, stock PATCH body (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { isError: false, messages: [], results: [] } }; });
  const res = await client.callTool({ name: "set_inventory", arguments: { listing_id: "243409", quantity: 7 } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.href, "https://marketplace-api.emag.bg/api-3/offer_stock/243409");
  assert.equal(seen.init.method, "PATCH");
  assert.equal(seen.init.headers.Authorization, "Basic " + Buffer.from("api-user@shop.ro:PASSWORDsecret1").toString("base64"));
  assert.deepEqual(JSON.parse(seen.init.body), { data: { stock: [{ warehouse_id: 1, value: 7 }] } });
});

test("emag: list_orders maps results (wire)", async () => {
  const client = await connect(() => ({ body: { isError: false, messages: [], results: [{ id: 5001, status: 2, date: "2026-09-20 10:00:00", products: [{ currency: "BGN" }] }] } }));
  const res = await client.callTool({ name: "list_orders", arguments: { status: "2" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.orders[0].id, "5001");
  assert.equal(res.structuredContent.orders[0].currency, "BGN");
});

test("emag: isError true is an error (wire)", async () => {
  const client = await connect(() => ({ body: { isError: true, messages: ["Invalid offer id"] } }));
  const res = await client.callTool({ name: "end_listing", arguments: { listing_id: "1" } });
  assert.equal(res.isError, true);
});
