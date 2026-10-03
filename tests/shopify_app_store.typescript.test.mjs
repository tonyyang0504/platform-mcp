import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/marketplaces/shopify_app_store.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
Object.assign(process.env, { PLATFORM_MCP_SHOPIFY_APP_STORE_ACCESS_TOKEN: "prtapi_secret_1", PLATFORM_MCP_SHOPIFY_APP_STORE_ORGANIZATION_ID: "4242" });

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("shopify app store: get_product queries app(id) on the organization endpoint (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { data: { app: { id: "gid://partners/App/1234", name: "Acme", apiKey: "k" } } } }; });
  const res = await client.callTool({ name: "get_product", arguments: { product_id: "gid://partners/App/1234" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.name, "Acme");
  assert.equal(seen.url.href, "https://partners.shopify.com/4242/api/2026-07/graphql.json");
  assert.deepEqual(JSON.parse(seen.init.body).variables, { id: "gid://partners/App/1234" });
  assert.equal(seen.init.headers["X-Shopify-Access-Token"], "prtapi_secret_1");
});
