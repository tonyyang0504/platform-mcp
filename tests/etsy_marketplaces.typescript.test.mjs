import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/marketplaces/etsy.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const a = SPEC.adapter;
  const creds = { client_id: "keystr", api_key: "keystr:etsy-shared-secret", refresh_token: "123.etsy-refresh", shop_id: "555" };
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, creds, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("etsy marketplaces: list_sales reads shop transactions (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => { seen.push({ url, init }); return url.pathname.endsWith("/oauth/token") ? { body: { access_token: "123.etsy-access", expires_in: 3600 } } : { body: { count: 1, results: [{ transaction_id: 7, listing_id: 1, title: "Mug", price: { amount: 1999, divisor: 100, currency_code: "USD" }, created_timestamp: 1700000000 }] } }; });
  const res = await client.callTool({ name: "list_sales", arguments: { limit: 10 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.sales[0].id, "7");
  assert.equal(res.structuredContent.sales[0].product_id, "1");
  const call = seen.find((s) => s.url.pathname === "/v3/application/shops/555/transactions");
  assert.equal(call.url.searchParams.get("limit"), "10");
  assert.equal(call.init.headers["x-api-key"], "keystr:etsy-shared-secret");
});
