import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/depop.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => (r.status === 204 ? "" : JSON.stringify(r.body ?? {})) }; };

process.env.PLATFORM_MCP_DEPOP_API_KEY = "DEPOP-apikey-secret";
process.env.PLATFORM_MCP_DEPOP_API_HOST = "partnerapi.depop.com";

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("depop: patch price by SKU with bearer key (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 204 }; });
  const res = await client.callTool({ name: "update_listing", arguments: { listing_id: "SKU-9", price: 24.5 } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.href, "https://partnerapi.depop.com/api/v1/products/by-sku/SKU-9/");
  assert.equal(seen.init.method, "PATCH");
  assert.equal(seen.init.headers.Authorization, "Bearer DEPOP-apikey-secret");
  assert.deepEqual(JSON.parse(seen.init.body), { price_amount: "24.5" });
});
