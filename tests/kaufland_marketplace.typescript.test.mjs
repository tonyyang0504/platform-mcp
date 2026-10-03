import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/kaufland_marketplace.json", import.meta.url), "utf8"));

test("get_product signs METHOD\\nURI\\nBODY\\nTS (wire)", async () => {
  let seen;
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { client_key: "CK", secret_key: "sec", storefront: "de" }, 50, "test", fakeFetch((url, init) => { seen = { url, init }; return { body: { data: { id_product: 7, title: "Toaster", units: [{ price: 2999, amount: 3 }] } } }; }), SPEC.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  const res = await client.callTool({ name: "get_product", arguments: { id: "7" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.first_offer_price, 2999);
  assert.equal(seen.url.searchParams.get("embedded"), "units");
  const h = seen.init.headers;
  assert.equal(h["Shop-Client-Key"], "CK");
  assert.equal(h["Shop-Signature"], crypto.createHmac("sha256", "sec").update(`GET\n${seen.url.toString()}\n\n${h["Shop-Timestamp"]}`).digest("hex"));
});
