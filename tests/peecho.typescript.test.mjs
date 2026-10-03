import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/peecho.json", import.meta.url), "utf8"));

test("quote body carries apiKey and a one-item list (wire)", async () => {
  let seen;
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { merchant_api_key: "K" }, 50, "test", fakeFetch((url, init) => { seen = { url, init }; return { body: { quotedItems: [{ offeringId: 1, totalItemPrice: 9.5 }] } }; }), SPEC.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  const res = await client.callTool({ name: "quote_shipping", arguments: { product_id: "1", country: "NL", quantity: 2 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.options[0].total_item_price, 9.5);
  assert.deepEqual(JSON.parse(seen.init.body), { apiKey: "K", countryCode: "NL", items: [{ offeringId: 1, quantity: 2 }] });
  assert.equal(seen.url.searchParams.get("merchantApiKey"), "K");
});
