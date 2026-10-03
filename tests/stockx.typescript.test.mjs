import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/stockx.json", import.meta.url), "utf8"));

async function connect(handler) {
  const creds = { api_key: "sx_key", client_id: "cid", client_secret: "sec", refresh_token: "rt", currency: "USD" };
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fakeFetch(handler), SPEC.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("stockx: refresh grant with audience, then PATCH listing with x-api-key (wire)", async () => {
  const calls = [];
  const client = await connect((url, init) => {
    calls.push({ url, init });
    if (url.hostname === "accounts.stockx.com") return { body: { access_token: "AT", expires_in: 43200 } };
    return { body: { listingId: "L-1", operationId: "op", operationStatus: "PENDING" } };
  });
  const res = await client.callTool({ name: "update_listing", arguments: { listing_id: "L-1", price: 150 } });
  assert.equal(res.isError, false);
  assert.match(String(calls[0].init.body), /grant_type=refresh_token/);
  assert.match(String(calls[0].init.body), /audience=gateway.stockx.com/);
  const last = calls.at(-1);
  assert.equal(last.url.href, "https://api.stockx.com/v2/selling/listings/L-1");
  assert.equal(last.init.headers.Authorization, "Bearer AT");
  assert.equal(last.init.headers["x-api-key"], "sx_key");
  assert.deepEqual(JSON.parse(last.init.body), { amount: "150", currencyCode: "USD" });
});
