import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (r.raw ?? JSON.stringify(r.body ?? {})) }; };
async function connect(spec, handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(spec);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}
const body = (init) => JSON.parse(init.body);

const SPEC = JSON.parse(readFileSync(new URL("../catalog/builder_tools/shopify.json", import.meta.url), "utf8"));
Object.assign(process.env, {"PLATFORM_MCP_SHOPIFY_ACCESS_TOKEN": "shpat_secret", "PLATFORM_MCP_SHOPIFY_SHOP": "demo-store"});

test("shopify list_items: GraphQL products with cursor variables (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { data: { products: { nodes: [{ id: "gid://shopify/Product/1", legacyResourceId: "1", title: "Shirt" }], pageInfo: { hasNextPage: true, endCursor: "eyJ" } } } } }; });
  const res = await client.callTool({ name: "list_items", arguments: { limit: 10, cursor: "abc" } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].url.href, "https://demo-store.myshopify.com/admin/api/2026-07/graphql.json");
  assert.equal(seen[0].init.headers["X-Shopify-Access-Token"], "shpat_secret");
  assert.deepEqual(body(seen[0].init).variables, { first: 10, after: "abc" });
  assert.equal(res.structuredContent.next_cursor, "eyJ");
  assert.equal(res.structuredContent.items[0].id, "1");
});

test("shopify create_item: product wrapper merges fields (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { status: 201, body: { product: { id: 632910392, status: "draft" } } }; });
  const res = await client.callTool({ name: "create_item", arguments: { title: "Tee", content: "<p>soft</p>", fields: { vendor: "Acme" } } });
  assert.deepEqual(body(seen[0].init), { product: { vendor: "Acme", title: "Tee", body_html: "<p>soft</p>" } });
  assert.equal(res.structuredContent.id, "632910392");
});
