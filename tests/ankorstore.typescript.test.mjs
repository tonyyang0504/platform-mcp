import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/ankorstore.json", import.meta.url), "utf8"));

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { client_id: "cid", client_secret: "sec" }, 50, "test", fakeFetch(handler), SPEC.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("mints a client-credentials token and reads a product (wire)", async () => {
  const calls = [];
  const client = await connect((url, init) => {
    calls.push({ url, init });
    if (url.pathname === "/oauth/token") return { body: { token_type: "Bearer", expires_in: 3600, access_token: "AT" } };
    return { body: { data: { type: "product", id: "c846", attributes: { name: "Example Product 2", wholesalePrice: 700, retailPrice: 900 } } } };
  });
  const res = await client.callTool({ name: "get_product", arguments: { id: "c846" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.title, "Example Product 2");
  assert.equal(res.structuredContent.wholesale_price_cents, 700);
  assert.match(String(calls[0].init.body), /grant_type=client_credentials/);
  const last = calls.at(-1);
  assert.equal(last.url.pathname, "/api/v1/products/c846");
  assert.equal(last.url.searchParams.get("include"), "productVariant");
  assert.equal(last.init.headers.Authorization, "Bearer AT");
  assert.equal(last.init.headers.Accept, "application/vnd.api+json");
});
