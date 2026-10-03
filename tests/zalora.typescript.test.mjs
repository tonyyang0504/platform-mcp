import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/zalora.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => JSON.stringify(r.body ?? {}) }; };
Object.assign(process.env, { PLATFORM_MCP_ZALORA_CLIENT_ID: "zal-app", PLATFORM_MCP_ZALORA_CLIENT_SECRET: "ZALSECRETvalue", PLATFORM_MCP_ZALORA_COUNTRY: "MY" });

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("zalora: stock array body after basic token (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => { seen.push({ url, init }); if (url.pathname === "/oauth/client-credentials") return { body: { access_token: "zal.at", expires_in: 3600 } }; return { body: [{ productId: 555, quantity: 8 }] }; });
  const res = await client.callTool({ name: "set_inventory", arguments: { listing_id: "555", quantity: 8 } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].init.headers.Authorization, "Basic " + Buffer.from("zal-app:ZALSECRETvalue").toString("base64"));
  const put = seen.find((s) => s.url.pathname === "/v2/stock/product");
  assert.equal(put.init.headers.Authorization, "Bearer zal.at");
  assert.deepEqual(JSON.parse(put.init.body), [{ productId: 555, quantity: 8 }]);
});
