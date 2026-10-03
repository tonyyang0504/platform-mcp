import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/onbuy.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => JSON.stringify(r.body ?? {}) }; };

process.env.PLATFORM_MCP_ONBUY_CONSUMER_KEY = "ck_live_123456";
process.env.PLATFORM_MCP_ONBUY_SECRET_KEY = "sk_live_abcdef";
process.env.PLATFORM_MCP_ONBUY_SITE_ID = "2000";

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("onbuy: form token login, raw Authorization, by-sku stock body (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => {
    seen.push({ url, init });
    if (url.pathname === "/v2/auth/request-token") return { body: { access_token: "4E7DREERR2189-TOKEN", expires_at: 1 } };
    return { body: { success: true, results: [{ sku: "S1", stock: 3 }] } };
  });
  const res = await client.callTool({ name: "set_inventory", arguments: { sku: "S1", quantity: 3 } });
  assert.equal(res.isError, false);
  assert.equal(new URLSearchParams(seen[0].init.body).get("consumer_key"), "ck_live_123456");
  const put = seen.find((s) => s.url.pathname === "/v2/listings/by-sku");
  assert.equal(put.init.method, "PUT");
  assert.equal(put.init.headers.Authorization, "4E7DREERR2189-TOKEN");
  assert.deepEqual(JSON.parse(put.init.body), { site_id: 2000, listings: [{ sku: "S1", stock: 3 }] });
});
