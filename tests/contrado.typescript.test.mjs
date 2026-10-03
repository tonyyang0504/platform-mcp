import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/contrado.json", import.meta.url), "utf8"));

async function connect(handler, creds = { api_key: "k" }) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fakeFetch(handler), SPEC.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_order", "get_product", "list_products", "me"]);
});

test("list_products unwraps data and sends X-Store-Id when configured (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { success: true, data: [{ storeProductId: 591879, storeProductName: "Silk Scarf", productThumb: "https://static.test/t.jpeg" }] } }; }, { api_key: "k", store_id: "88" });
  const res = await client.callTool({ name: "list_products", arguments: { page: 3, limit: 20 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.products[0].id, "591879");
  assert.equal(seen.url.searchParams.get("PageNumber"), "3");
  assert.equal(seen.init.headers["X-API-KEY"], "k");
  assert.equal(seen.init.headers["X-Store-Id"], "88");
});

test("success:false inside a 200 is an isError result (wire)", async () => {
  const client = await connect(() => ({ body: { success: false, message: "Invalid argument provided", data: null } }));
  const res = await client.callTool({ name: "get_order", arguments: { id: "1" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "upstream_error");
});
