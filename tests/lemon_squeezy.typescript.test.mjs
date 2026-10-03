import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/marketplaces/lemon_squeezy.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { api_key: "ls-secret-key-123", store_id: "7" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("lemon squeezy: full refund posts a JSON:API document without amount (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { data: { type: "orders", id: "5", attributes: { refunded_amount: 1199, currency: "USD", status: "refunded" } } } }; });
  const res = await client.callTool({ name: "refund", arguments: { sale_id: "5" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "refunded");
  assert.equal(seen.url.href, "https://api.lemonsqueezy.com/v1/orders/5/refund");
  assert.deepEqual(JSON.parse(seen.init.body), { data: { type: "orders", id: "5" } });
  assert.equal(seen.init.headers.Authorization, "Bearer ls-secret-key-123");
});
