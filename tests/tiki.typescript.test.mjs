import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/tiki.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => JSON.stringify(r.body ?? {}) }; };
Object.assign(process.env, { PLATFORM_MCP_TIKI_CLIENT_ID: "7590139168389961", PLATFORM_MCP_TIKI_CLIENT_SECRET: "tfSl0c6VFv3fAB_z9F", PLATFORM_MCP_TIKI_WAREHOUSE_ID: "1034" });

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("tiki: updateSku price after basic token (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => { seen.push({ url, init }); if (url.pathname === "/sc/oauth2/token") return { body: { access_token: "tiki.at", expires_in: 3599 } }; return { body: {} }; });
  const res = await client.callTool({ name: "update_listing", arguments: { listing_id: "2166152", price: 100000 } });
  assert.equal(res.isError, false);
  const put = seen.find((s) => s.url.pathname === "/integration/v2/products/updateSku");
  assert.equal(put.init.headers.Authorization, "Bearer tiki.at");
  assert.deepEqual(JSON.parse(put.init.body), { product_id: 2166152, price: 100000 });
});
