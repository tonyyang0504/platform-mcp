import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/etsy.json", import.meta.url), "utf8"));
const TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token";
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const tokenOk = { body: { access_token: "12345678.ACCESS1", token_type: "Bearer", expires_in: 3600, refresh_token: "12345678.NEXT" } };

process.env.PLATFORM_MCP_ETSY_CLIENT_ID = "1aa2bb33c44d55eeeeee6fff";
process.env.PLATFORM_MCP_ETSY_API_KEY = "1aa2bb33c44d55eeeeee6fff:a1b2c3d4e5";
process.env.PLATFORM_MCP_ETSY_REFRESH_TOKEN = "12345678.REFRESHsecretVALUE";
process.env.PLATFORM_MCP_ETSY_SHOP_ID = "5555";
process.env.PLATFORM_MCP_ETSY_TAXONOMY_ID = "1633";
process.env.PLATFORM_MCP_ETSY_WHO_MADE = "i_did";
process.env.PLATFORM_MCP_ETSY_WHEN_MADE = "made_to_order";
process.env.PLATFORM_MCP_ETSY_SHIPPING_PROFILE_ID = "777";
process.env.PLATFORM_MCP_ETSY_READINESS_STATE_ID = "888";

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("etsy: refresh grant in the form body, bearer + x-api-key on the call (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => { seen.push({ url, init }); return url.href === TOKEN_URL ? tokenOk : { body: { user_id: 12345678, shop_id: 5555 } }; });
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["create_listing", "end_listing", "list_orders", "mark_shipped", "me", "update_listing"]);
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, false);
  const [tok, call] = seen;
  assert.equal(tok.url.href, TOKEN_URL);
  assert.deepEqual(Object.fromEntries(new URLSearchParams(tok.init.body)), { grant_type: "refresh_token", refresh_token: "12345678.REFRESHsecretVALUE", client_id: "1aa2bb33c44d55eeeeee6fff" });
  assert.equal(tok.init.headers.Authorization, undefined);
  assert.equal(call.url.href, "https://api.etsy.com/v3/application/users/me");
  assert.equal(call.init.headers.Authorization, "Bearer 12345678.ACCESS1");
  assert.equal(call.init.headers["x-api-key"], "1aa2bb33c44d55eeeeee6fff:a1b2c3d4e5");
});

test("etsy: list_orders maps shop receipts (wire)", async () => {
  let seen;
  const client = await connect((url) => { if (url.href === TOKEN_URL) return tokenOk; seen = url; return { body: { count: 1, results: [{ receipt_id: 1234567890, status: "paid", created_timestamp: 1758700000, grandtotal: { amount: 2999, divisor: 100, currency_code: "USD" }, shipments: [{ tracking_code: "9400111" }] }] } }; });
  const res = await client.callTool({ name: "list_orders", arguments: { since: "1758600000", limit: 10, page: 2 } });
  assert.equal(res.isError, false);
  assert.equal(seen.origin + seen.pathname, "https://api.etsy.com/v3/application/shops/5555/receipts");
  assert.equal(seen.searchParams.get("min_created"), "1758600000");
  assert.equal(seen.searchParams.get("offset"), "10");
  const o = res.structuredContent.orders[0];
  assert.equal(o.id, "1234567890");
  assert.equal(o.currency, "USD");
  assert.equal(o.tracking_number, "9400111");
  assert.equal(res.structuredContent.total, 1);
});

test("etsy: mark_shipped posts tracking_code + carrier_name (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { if (url.href === TOKEN_URL) return tokenOk; seen = { url, init }; return { body: { receipt_id: 1234567890, status: "completed" } }; });
  const res = await client.callTool({ name: "mark_shipped", arguments: { order_id: "1234567890", carrier: "usps", tracking_number: "9400111" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "completed");
  assert.equal(seen.url.href, "https://api.etsy.com/v3/application/shops/5555/receipts/1234567890/tracking");
  assert.equal(seen.init.method, "POST");
  assert.deepEqual(JSON.parse(seen.init.body), { tracking_code: "9400111", carrier_name: "usps" });
});

test("etsy: refused refresh token is an auth_error without secrets (wire)", async () => {
  const client = await connect(() => ({ status: 400, body: { error: "invalid_grant", error_description: "Invalid refresh token" } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  const text = JSON.stringify(res);
  assert.ok(!text.includes("REFRESHsecretVALUE") && !text.includes("a1b2c3d4e5"));
});

test("etsy: create_listing and end_listing send form-encoded bodies (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => { if (url.href === TOKEN_URL) return tokenOk; seen.push({ url, init }); return { body: { listing_id: 1136716168, state: init.method === "POST" ? "draft" : "inactive", url: "https://www.etsy.com/listing/1136716168/yo-yo" } }; });
  let res = await client.callTool({ name: "create_listing", arguments: { title: "Wooden yo-yo", description: "Hand turned", price: 21.99, quantity: 5 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.listing_id, "1136716168");
  assert.equal(res.structuredContent.status, "draft");
  assert.equal(seen[0].url.href, "https://api.etsy.com/v3/application/shops/5555/listings");
  assert.equal(seen[0].init.headers["Content-Type"], "application/x-www-form-urlencoded");
  assert.deepEqual(Object.fromEntries(new URLSearchParams(seen[0].init.body)), { title: "Wooden yo-yo", description: "Hand turned", price: "21.99", quantity: "5", who_made: "i_did", when_made: "made_to_order", taxonomy_id: "1633", type: "physical", shipping_profile_id: "777", readiness_state_id: "888" });
  res = await client.callTool({ name: "end_listing", arguments: { listing_id: "1136716168" } });
  assert.equal(res.structuredContent.status, "inactive");
  assert.equal(seen[1].init.method, "PATCH");
  assert.equal(seen[1].init.body, "state=inactive");
  assert.equal(seen[1].init.headers["Content-Type"], "application/x-www-form-urlencoded");
});
