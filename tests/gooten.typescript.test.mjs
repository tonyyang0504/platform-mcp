import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/gooten.json", import.meta.url), "utf8"));

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { recipe_id: "RID" }, 50, "test", fakeFetch(handler), SPEC.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("recipeid query, print-ready products, HadError envelope (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return url.searchParams.get("page") === "9" ? { body: { HadError: true, Errors: [{ ErrorMessage: "bad page" }] } } : { body: { PageCount: 5, Page: 1, Products: [{ ProductName: "000-AKOO", NumberOfVariants: 1 }], HadError: false } }; });
  const res = await client.callTool({ name: "list_products", arguments: {} });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.products[0].id, "000-AKOO");
  assert.equal(seen.searchParams.get("recipeid"), "RID");
  assert.equal(seen.pathname, "/api/v/5/source/api/prpproducts/");
  const bad = await client.callTool({ name: "list_products", arguments: { page: 9 } });
  assert.equal(bad.isError, true);
});
