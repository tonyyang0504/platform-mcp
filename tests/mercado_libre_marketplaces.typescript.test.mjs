import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/marketplaces/mercado_libre.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const a = SPEC.adapter;
  const creds = { client_id: "123", client_secret: "ml-client-secret", refresh_token: "TG-ml-refresh-1", seller_id: "999" };
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, creds, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("mercado libre marketplaces: get_product maps the item (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => { seen.push({ url, init }); return url.pathname === "/oauth/token" ? { body: { access_token: "APP_USR-ml-access", expires_in: 21600 } } : { body: { id: "MLA1", title: "Mate", price: 1000, currency_id: "ARS", status: "active", permalink: "https://articulo.mercadolibre.com.ar/MLA-1" } }; });
  const res = await client.callTool({ name: "get_product", arguments: { product_id: "MLA1" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.currency, "ARS");
  const call = seen.find((s) => s.url.pathname === "/items/MLA1");
  assert.equal(call.init.headers.Authorization, "Bearer APP_USR-ml-access");
});
