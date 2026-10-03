import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/allegro.json", import.meta.url), "utf8"));
const TOKEN_URL = "https://allegro.pl/auth/oauth/token";
const VND = "application/vnd.allegro.public.v1+json";
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const tok = (a, r) => ({ body: { access_token: a, token_type: "bearer", refresh_token: r, expires_in: 43199 } });

process.env.PLATFORM_MCP_ALLEGRO_CLIENT_ID = "cid-123";
process.env.PLATFORM_MCP_ALLEGRO_CLIENT_SECRET = "SECRETvalue";
process.env.PLATFORM_MCP_ALLEGRO_REFRESH_TOKEN = "R1-REFRESHsecret";
process.env.PLATFORM_MCP_ALLEGRO_CURRENCY = "PLN";
delete process.env.PLATFORM_MCP_STATE_DIR;

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("allegro: Basic refresh, vendor Accept, rotated refresh token used on re-mint (wire)", async () => {
  const seen = []; let meCalls = 0; let n = 0;
  const client = await connect((url, init) => {
    seen.push({ url, init });
    if (url.href === TOKEN_URL) { n += 1; return tok(`A${n}`, `R${n + 1}-REFRESHsecret`); }
    meCalls += 1; return meCalls === 2 ? { status: 401, body: { error: "invalid_token" } } : { body: { id: "43120000", login: "seller" } };
  });
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["end_listing", "list_orders", "mark_shipped", "me", "set_inventory", "update_listing"]);
  assert.equal((await client.callTool({ name: "me", arguments: {} })).isError, false);
  assert.equal((await client.callTool({ name: "me", arguments: {} })).isError, false);
  const tokens = seen.filter((s) => s.url.href === TOKEN_URL);
  assert.equal(tokens[0].init.headers.Authorization, "Basic " + Buffer.from("cid-123:SECRETvalue").toString("base64"));
  assert.deepEqual(tokens.map((t) => new URLSearchParams(t.init.body).get("refresh_token")), ["R1-REFRESHsecret", "R2-REFRESHsecret"]);
  const api = seen.find((s) => s.url.href === "https://api.allegro.pl/me");
  assert.equal(api.init.headers.Accept, VND);
  assert.equal(api.init.headers.Authorization, "Bearer A1");
});

test("allegro: update_listing keeps the vendor Content-Type and sends the documented patch (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { if (url.href === TOKEN_URL) return tok("A1", "R2"); seen = { url, init }; return { body: { id: "7766554433" } }; });
  const res = await client.callTool({ name: "update_listing", arguments: { listing_id: "7766554433", price: 220.85, quantity: 10 } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.href, "https://api.allegro.pl/sale/product-offers/7766554433");
  assert.equal(seen.init.method, "PATCH");
  assert.equal(seen.init.headers["Content-Type"], VND);
  assert.deepEqual(JSON.parse(seen.init.body), { sellingMode: { price: { amount: "220.85", currency: "PLN" } }, stock: { available: 10 } });
});

test("allegro: list_orders maps checkout forms (wire)", async () => {
  let seen;
  const client = await connect((url) => { if (url.href === TOKEN_URL) return tok("A1", "R2"); seen = url; return { body: { count: 1, totalCount: 1, checkoutForms: [{ id: "cf-1", status: "READY_FOR_PROCESSING", fulfillment: { status: "NEW" }, summary: { totalToPay: { amount: "123.45", currency: "PLN" } }, lineItems: [{ boughtAt: "2026-09-20T10:00:00.000Z" }] }] } }; });
  const res = await client.callTool({ name: "list_orders", arguments: { status: "NEW", since: "2026-09-01T00:00:00Z" } });
  assert.equal(res.isError, false);
  assert.equal(seen.searchParams.get("fulfillment.status"), "NEW");
  assert.equal(seen.searchParams.get("lineItems.boughtAt.gte"), "2026-09-01T00:00:00Z");
  assert.equal(res.structuredContent.orders[0].id, "cf-1");
  assert.equal(res.structuredContent.orders[0].total, "123.45");
  assert.equal(res.structuredContent.total, 1);
});

test("allegro: used refresh token is an auth_error without secrets (wire)", async () => {
  const client = await connect(() => ({ status: 400, body: { error: "invalid_grant", error_description: "Invalid refresh token: R1-REFRESHsecret" } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  const text = JSON.stringify(res);
  assert.ok(!text.includes("R1-REFRESHsecret") && !text.includes("SECRETvalue"));
});
