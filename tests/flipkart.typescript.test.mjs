import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/flipkart.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => JSON.stringify(r.body ?? {}) }; };
process.env.PLATFORM_MCP_FLIPKART_ACCESS_TOKEN = "FK-token-f638949a";

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("flipkart: list_orders builds the filter body (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { shipments: [{ shipmentId: "S1", orderItems: [{ orderId: "OD1", status: "APPROVED" }] }] } }; });
  const res = await client.callTool({ name: "list_orders", arguments: { status: "APPROVED" } });
  assert.equal(res.isError, false);
  assert.equal(seen.init.headers.Authorization, "Bearer FK-token-f638949a");
  assert.deepEqual(JSON.parse(seen.init.body), { filter: { type: "preDispatch", states: ["APPROVED"] }, pagination: { pageSize: 20 } });
  assert.equal(res.structuredContent.orders[0].id, "OD1");
});
