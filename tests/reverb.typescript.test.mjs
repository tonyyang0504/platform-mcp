import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/reverb.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => JSON.stringify(r.body ?? {}) }; };
process.env.PLATFORM_MCP_REVERB_TOKEN = "774c5112345abcd3f32e662e885e0436";
process.env.PLATFORM_MCP_REVERB_CURRENCY = "USD";

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("reverb: ship order with hal+json headers (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: {} }; });
  const res = await client.callTool({ name: "mark_shipped", arguments: { order_id: "2", carrier: "USPS", tracking_number: "123" } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.href, "https://api.reverb.com/api/my/orders/selling/2/ship");
  assert.equal(seen.init.headers["Accept-Version"], "3.0");
  assert.equal(seen.init.headers["Content-Type"], "application/hal+json");
  assert.deepEqual(JSON.parse(seen.init.body), { provider: "USPS", tracking_number: "123", send_notification: true });
});
