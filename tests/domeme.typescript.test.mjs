import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/domeme.json", import.meta.url), "utf8"));

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_key: "K" }, 50, "test", fakeFetch(handler), SPEC.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("aid query key, supply market, errors body is a tool error (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return url.searchParams.get("kw") === "bad" ? { body: { errors: { code: "401", dcode: "UNAUTHORIZED" } } } : { body: { domeggook: { header: { numberOfItems: 1 }, list: { item: [{ no: 1, title: "t", price: 100 }] } } } }; });
  const res = await client.callTool({ name: "list_products", arguments: { query: "t" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.products[0].id, "1");
  assert.equal(seen.searchParams.get("aid"), "K");
  assert.equal(seen.searchParams.get("market"), "supply");
  const bad = await client.callTool({ name: "list_products", arguments: { query: "bad" } });
  assert.equal(bad.isError, true);
});
