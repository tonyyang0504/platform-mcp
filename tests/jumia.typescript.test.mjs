import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/jumia.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => JSON.stringify(r.body ?? {}) }; };
process.env.PLATFORM_MCP_JUMIA_CLIENT_ID = "jumia-self-app";
process.env.PLATFORM_MCP_JUMIA_REFRESH_TOKEN = "RT1-refresh-secret";
delete process.env.PLATFORM_MCP_STATE_DIR;

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("jumia: refresh grant then stock feed (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => { seen.push({ url, init }); if (url.pathname === "/token") return { body: { access_token: "JWT1", expires_in: 86399, refresh_token: "RT2" } }; return { status: 201, body: { feedId: "f1" } }; });
  const res = await client.callTool({ name: "set_inventory", arguments: { sku: "S1", listing_id: "sid-1", quantity: 3 } });
  assert.equal(res.isError, false);
  const tok = new URLSearchParams(seen[0].init.body);
  assert.equal(tok.get("grant_type"), "refresh_token");
  assert.equal(tok.get("client_id"), "jumia-self-app");
  const feed = seen.find((s) => s.url.pathname === "/feeds/products/stock");
  assert.equal(feed.init.headers.Authorization, "Bearer JWT1");
  assert.deepEqual(JSON.parse(feed.init.body), { products: [{ sellerSku: "S1", id: "sid-1", stock: 3 }] });
});
