import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/base_jp.json", import.meta.url), "utf8"));
const CREDS = { client_id: "cid-base-1", client_secret: "SECRET-base-1", refresh_token: "REFRESH-base-1", redirect_uri: "https://app.example/base/callback" };

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", fakeFetch(handler), a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

const hdr = (init, name) => { const h = init.headers ?? {}; const k = Object.keys(h).find((x) => x.toLowerCase() === name.toLowerCase()); return k ? h[k] : undefined; };

test("base_jp: refresh carries redirect_uri, then the item is read with the bearer token", async () => {
  const calls = [];
  const client = await connect((url, init) => {
    calls.push({ url, init });
    if (url.pathname === "/1/oauth/token") return { body: { access_token: "ACCESS-base", expires_in: 3600, refresh_token: "REFRESH-base-2" } };
    return { body: { item: { item_id: 1234, title: "Tシャツ", price: 3900, stock: 10, identifier: "TS-1" } } };
  });
  const res = await client.callTool({ name: "get_product", arguments: { id: "1234" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "1234");
  assert.equal(res.structuredContent.sku, "TS-1");
  const form = Object.fromEntries(new URLSearchParams(String(calls[0].init.body)));
  assert.equal(form.grant_type, "refresh_token");
  assert.equal(form.redirect_uri, "https://app.example/base/callback");
  assert.equal(form.client_id, "cid-base-1");
  assert.equal(form.refresh_token, "REFRESH-base-1");
  assert.equal(calls[1].url.pathname, "/1/items/detail/1234");
  assert.equal(hdr(calls[1].init, "Authorization"), "Bearer ACCESS-base");
});

test("base_jp: get_order maps dispatch status", async () => {
  const client = await connect((url) => url.pathname === "/1/oauth/token"
    ? { body: { access_token: "ACCESS-base", expires_in: 3600 } }
    : { body: { order: { unique_key: "154D88A39E454289", total: 8800, dispatch_status: "shipping", tracking_number: "1234" } } });
  const res = await client.callTool({ name: "get_order", arguments: { id: "154D88A39E454289" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "shipping");
  assert.equal(res.structuredContent.currency, "JPY");
});
