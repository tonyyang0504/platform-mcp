import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/apliiq.json", import.meta.url), "utf8"));

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { app_id: "APP1", shared_secret: "sec" }, 50, "test", fakeFetch(handler), SPEC.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("signs GET requests with x-apliiq-auth and maps a product (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { Id: 162, Name: "Womens T-Shirt", SKU: "6004", Price: 11.5, Currency_Code: "USD" } }; });
  const res = await client.callTool({ name: "get_product", arguments: { id: "162" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "162");
  assert.equal(seen.url.pathname, "/v1/Product/162");
  const [scheme, rest] = seen.init.headers.Authorization.split(" ");
  const [rts, sig, appid, state] = rest.split(":");
  assert.equal(scheme, "x-apliiq-auth");
  assert.equal(appid, "APP1");
  assert.equal(sig, crypto.createHmac("sha256", "sec").update(`APP1${rts}${state}`).digest("base64"));
});
