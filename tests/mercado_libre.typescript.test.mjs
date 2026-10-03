import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/mercado_libre.json", import.meta.url), "utf8"));
const TOKEN_URL = "https://api.mercadolibre.com/oauth/token";
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const tokenOk = { body: { access_token: "APP_USR-A1", token_type: "Bearer", expires_in: 21600, refresh_token: "TG-REFRESHsecret-2" } };

process.env.PLATFORM_MCP_MERCADO_LIBRE_CLIENT_ID = "1234567890";
process.env.PLATFORM_MCP_MERCADO_LIBRE_CLIENT_SECRET = "SECRETvalue";
process.env.PLATFORM_MCP_MERCADO_LIBRE_REFRESH_TOKEN = "TG-REFRESHsecret-1";
process.env.PLATFORM_MCP_MERCADO_LIBRE_SELLER_ID = "1108966308";
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

test("mercado_libre: refresh with client credentials in the body, then bearer (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => { seen.push({ url, init }); return url.href === TOKEN_URL ? tokenOk : { body: { id: 1108966308, nickname: "SELLER" } }; });
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["end_listing", "list_orders", "me", "set_inventory", "update_listing"]);
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, false);
  const [tok, call] = seen;
  assert.deepEqual(Object.fromEntries(new URLSearchParams(tok.init.body)), { grant_type: "refresh_token", refresh_token: "TG-REFRESHsecret-1", client_id: "1234567890", client_secret: "SECRETvalue" });
  assert.equal(tok.init.headers.Authorization, undefined);
  assert.equal(call.url.href, "https://api.mercadolibre.com/users/me");
  assert.equal(call.init.headers.Authorization, "Bearer APP_USR-A1");
});

test("mercado_libre: list_orders maps the order search (wire)", async () => {
  let seen;
  const client = await connect((url) => { if (url.href === TOKEN_URL) return tokenOk; seen = url; return { body: { results: [{ id: 2000003508419013, status: "paid", total_amount: 880, currency_id: "MXN", date_created: "2026-09-20T10:30:00.000-03:00" }], paging: { total: 1, offset: 0, limit: 50 } } }; });
  const res = await client.callTool({ name: "list_orders", arguments: { status: "paid" } });
  assert.equal(res.isError, false);
  assert.equal(seen.origin + seen.pathname, "https://api.mercadolibre.com/orders/search");
  assert.equal(seen.searchParams.get("seller"), "1108966308");
  assert.equal(seen.searchParams.get("order.status"), "paid");
  assert.equal(res.structuredContent.orders[0].id, "2000003508419013");
  assert.equal(res.structuredContent.orders[0].currency, "MXN");
  assert.equal(res.structuredContent.total, 1);
});

test("mercado_libre: set_inventory PUTs available_quantity as JSON (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { if (url.href === TOKEN_URL) return tokenOk; seen = { url, init }; return { body: { id: "MLA1136716168", status: "active" } }; });
  const res = await client.callTool({ name: "set_inventory", arguments: { listing_id: "MLA1136716168", quantity: 6 } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.href, "https://api.mercadolibre.com/items/MLA1136716168");
  assert.equal(seen.init.method, "PUT");
  assert.equal(seen.init.headers["Content-Type"], "application/json");
  assert.deepEqual(JSON.parse(seen.init.body), { available_quantity: 6 });
});

test("mercado_libre: used refresh token is an auth_error without secrets (wire)", async () => {
  const client = await connect(() => ({ status: 400, body: { error: "invalid_grant", error_description: "Error validating grant.", refresh_token: "TG-REFRESHsecret-1" } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  const text = JSON.stringify(res);
  assert.ok(!text.includes("TG-REFRESHsecret-1") && !text.includes("SECRETvalue"));
});
