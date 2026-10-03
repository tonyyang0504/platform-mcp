import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/manomano.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => (r.status === 204 ? "" : JSON.stringify(r.body ?? {})) }; };

process.env.PLATFORM_MCP_MANOMANO_API_KEY = "MMKEY-u4EAhgExMQSu";
process.env.PLATFORM_MCP_MANOMANO_SELLER_CONTRACT_ID = "110841";

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("manomano: update_offers body and headers (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { request_id: "r-1" } }; });
  const res = await client.callTool({ name: "set_inventory", arguments: { sku: "ABC-24345", quantity: 333 } });
  assert.equal(res.isError, false);
  assert.equal(seen.init.method, "PATCH");
  assert.equal(seen.init.headers["x-api-key"], "MMKEY-u4EAhgExMQSu");
  assert.equal(seen.init.headers["x-thirdparty-name"], "platform-mcp_0.1.0");
  assert.deepEqual(JSON.parse(seen.init.body), { content: [{ seller_contract_id: 110841, items: [{ sku: "ABC-24345", stock: { quantity: 333 } }] }] });
});

test("manomano: mark_shipped posts one shipping (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 204 }; });
  const res = await client.callTool({ name: "mark_shipped", arguments: { order_id: "M1", carrier: "UPS", tracking_number: "1Z" } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.pathname, "/orders/v1/shippings");
  assert.deepEqual(JSON.parse(seen.init.body), [{ order_reference: "M1", seller_contract_id: 110841, carrier: "UPS", tracking_number: "1Z" }]);
});
