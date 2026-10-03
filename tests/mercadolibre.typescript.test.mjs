import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/automotive/mercadolibre.json", import.meta.url), "utf8"));
const CREDS = { client_id: "123", client_secret: "ml-client-secret", refresh_token: "TG-ml-refresh-1" };
const fakeFetch = (handler, seen) => async (url, init) => { const u = new URL(url); seen.push({ url: u, init }); const r = handler(u, init); return { status: r.status ?? 200, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null) }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const a = SPEC.adapter;
  const seen = [];
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", fakeFetch(handler, seen), a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  client.seen = seen;
  return client;
}
const hdr = (init, name) => { const h = init.headers || {}; const k = Object.keys(h).find((x) => x.toLowerCase() === name.toLowerCase()); return k ? h[k] : undefined; };

test("mercadolibre automotive: get_listing reads an item (wire)", async () => {
  const client = await connect((url) => url.pathname === "/oauth/token" ? { body: { access_token: "APP_USR-ml-access", expires_in: 21600 } } : { body: { id: "MLB1045563828", title: "Gol", price: 45000, currency_id: "BRL", permalink: "https://carro.mercadolivre.com.br/MLB-1045563828" } });
  const res = await client.callTool({ name: "get_listing", arguments: { listing_id: "MLB1045563828" } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.equal(res.structuredContent.currency, "BRL");
  const call = client.seen.find((s) => s.url.pathname === "/items/MLB1045563828");
  assert.equal(hdr(call.init, "Authorization"), "Bearer APP_USR-ml-access");
});
