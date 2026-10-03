import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/ebay.json", import.meta.url), "utf8"));
const TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token";
const SCOPES = "https://api.ebay.com/oauth/api_scope/sell.inventory https://api.ebay.com/oauth/api_scope/sell.fulfillment https://api.ebay.com/oauth/api_scope/sell.account";
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const tokenOk = { body: { access_token: "v^1.1#ACCESS", expires_in: 7200, token_type: "User Access Token" } };

process.env.PLATFORM_MCP_EBAY_CLIENT_ID = "MyApp-PRD-1234";
process.env.PLATFORM_MCP_EBAY_CLIENT_SECRET = "PRD-CERTsecretVALUE";
process.env.PLATFORM_MCP_EBAY_REFRESH_TOKEN = "v^1.1#REFRESHsecretVALUE";
process.env.PLATFORM_MCP_EBAY_CURRENCY = "USD";

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("ebay: refresh grant with Basic client auth and scope, then bearer (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => { seen.push({ url, init }); return url.href === TOKEN_URL ? tokenOk : { body: { sellerRegistrationCompleted: true } }; });
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["end_listing", "list_orders", "me", "set_inventory", "update_listing"]);
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, false);
  const [tok, call] = seen;
  assert.equal(tok.init.headers.Authorization, "Basic " + Buffer.from("MyApp-PRD-1234:PRD-CERTsecretVALUE").toString("base64"));
  assert.deepEqual(Object.fromEntries(new URLSearchParams(tok.init.body)), { grant_type: "refresh_token", refresh_token: "v^1.1#REFRESHsecretVALUE", scope: SCOPES });
  assert.equal(call.url.href, "https://api.ebay.com/sell/account/v1/privilege");
  assert.equal(call.init.headers.Authorization, "Bearer v^1.1#ACCESS");
});

test("ebay: list_orders maps getOrders (wire)", async () => {
  let seen;
  const client = await connect((url) => { if (url.href === TOKEN_URL) return tokenOk; seen = url; return { body: { total: 1, orders: [{ orderId: "05-12345-67890", orderFulfillmentStatus: "NOT_STARTED", creationDate: "2026-09-20T10:00:00.000Z", pricingSummary: { total: { value: "25.98", currency: "USD" } } }] } }; });
  const res = await client.callTool({ name: "list_orders", arguments: { limit: 10, page: 3 } });
  assert.equal(res.isError, false);
  assert.equal(seen.origin + seen.pathname, "https://api.ebay.com/sell/fulfillment/v1/order");
  assert.equal(seen.searchParams.get("limit"), "10");
  assert.equal(seen.searchParams.get("offset"), "20");
  assert.equal(res.structuredContent.orders[0].id, "05-12345-67890");
  assert.equal(res.structuredContent.orders[0].total, "25.98");
  assert.equal(res.structuredContent.total, 1);
});

test("ebay: update_listing builds the bulk_update_price_quantity body (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { if (url.href === TOKEN_URL) return tokenOk; seen = { url, init }; return { body: { responses: [{ statusCode: 200, offerId: "123456" }] } }; });
  const res = await client.callTool({ name: "update_listing", arguments: { listing_id: "123456", price: 19.5, quantity: 4 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "submitted");
  assert.equal(seen.url.href, "https://api.ebay.com/sell/inventory/v1/bulk_update_price_quantity");
  assert.deepEqual(JSON.parse(seen.init.body), { requests: [{ offers: [{ offerId: "123456", availableQuantity: 4, price: { value: "19.5", currency: "USD" } }] }] });
});

test("ebay: refused refresh token is an auth_error without secrets (wire)", async () => {
  const client = await connect(() => ({ status: 400, body: { error: "invalid_grant", error_description: "the provided authorization refresh token is invalid or was issued to another client" } }));
  const res = await client.callTool({ name: "end_listing", arguments: { listing_id: "123456" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  const text = JSON.stringify(res);
  assert.ok(!text.includes("REFRESHsecretVALUE") && !text.includes("CERTsecretVALUE"));
});
