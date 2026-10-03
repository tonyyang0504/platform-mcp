import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/sticker_mule.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler, creds = { api_key: "smk-secret" }) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["create_order", "list_products", "me"]);
  assert.equal(tools.find((t) => t.name === "create_order").annotations.destructiveHint, true);
});

test("list_products pages by offset and maps items (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { items: [{ id: "456", name: "Logo stickers", productId: 12, productName: "Die cut stickers", retailPrice: 79, artworkUrls: ["https://cdn.stickermule.com/a.png"] }], canLoadMore: false } }; });
  const res = await client.callTool({ name: "list_products", arguments: { page: 2, limit: 5 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.products[0].id, "456");
  assert.equal(res.structuredContent.products[0].title, "Die cut stickers");
  assert.equal(seen.url.pathname, "/api/items");
  assert.equal(seen.url.searchParams.get("offset"), "5");
  assert.equal(seen.init.headers.Authorization, "Bearer smk-secret");
});

test("create_order body carries addressId and paymentId (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { order: { number: "R1" } } }; }, { api_key: "smk-secret", payment_id: "7" });
  const res = await client.callTool({ name: "create_order", arguments: { items: [{ id: "456", quantity: 50 }], shipping_address: { id: "22" } } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "R1");
  assert.deepEqual(JSON.parse(seen.init.body), { items: [{ id: "456", quantity: 50 }], addressId: "22", paymentId: "7" });
});

test("forbidden key is an isError result (wire)", async () => {
  const client = await connect(() => ({ status: 403, body: { type: "ForbiddenError", message: "bad smk-secret" } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.equal(JSON.stringify(res.structuredContent).includes("smk-secret"), false);
});
