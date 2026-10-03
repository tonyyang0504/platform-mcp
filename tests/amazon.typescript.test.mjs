import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/amazon.json", import.meta.url), "utf8"));
const TOKEN_URL = "https://api.amazon.com/auth/o2/token";
const HOST = "https://sellingpartnerapi-eu.amazon.com";
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const tokenOk = { body: { access_token: "Atza|ACCESS", token_type: "bearer", expires_in: 3600, refresh_token: "Atzr|REFRESHsecretVALUE" } };

process.env.PLATFORM_MCP_AMAZON_CLIENT_ID = "amzn1.application-oa2-client.abc";
process.env.PLATFORM_MCP_AMAZON_CLIENT_SECRET = "amzn1.oa2-cs.v1.SECRETvalue";
process.env.PLATFORM_MCP_AMAZON_REFRESH_TOKEN = "Atzr|REFRESHsecretVALUE";
process.env.PLATFORM_MCP_AMAZON_REGION = "eu";
process.env.PLATFORM_MCP_AMAZON_SELLER_ID = "A2SELLER";
process.env.PLATFORM_MCP_AMAZON_MARKETPLACE_ID = "A1F83G8C2ARO7P";
process.env.PLATFORM_MCP_AMAZON_CURRENCY = "GBP";

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("amazon: LWA refresh in the body, token in x-amz-access-token without Bearer (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => { seen.push({ url, init }); return url.href === TOKEN_URL ? tokenOk : { body: { payload: [{ marketplace: { id: "A1F83G8C2ARO7P" } }] } }; });
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["end_listing", "list_orders", "me", "set_inventory", "update_listing"]);
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, false);
  const [tok, call] = seen;
  assert.deepEqual(Object.fromEntries(new URLSearchParams(tok.init.body)), { grant_type: "refresh_token", refresh_token: "Atzr|REFRESHsecretVALUE", client_id: "amzn1.application-oa2-client.abc", client_secret: "amzn1.oa2-cs.v1.SECRETvalue" });
  assert.equal(tok.init.headers.Authorization, undefined);
  assert.equal(call.url.href, `${HOST}/sellers/v1/marketplaceParticipations`);
  assert.equal(call.init.headers["x-amz-access-token"], "Atza|ACCESS");
  assert.equal(call.init.headers.Authorization, undefined);
});

test("amazon: list_orders maps Orders v0 (wire)", async () => {
  let seen;
  const client = await connect((url) => { if (url.href === TOKEN_URL) return tokenOk; seen = url; return { body: { payload: { Orders: [{ AmazonOrderId: "202-1234567-1234567", OrderStatus: "Unshipped", PurchaseDate: "2026-09-20T10:00:00Z", OrderTotal: { CurrencyCode: "GBP", Amount: "12.99" } }] } } }; });
  const res = await client.callTool({ name: "list_orders", arguments: { since: "2026-09-01T00:00:00Z", status: "Unshipped" } });
  assert.equal(res.isError, false);
  assert.equal(seen.origin + seen.pathname, `${HOST}/orders/v0/orders`);
  assert.equal(seen.searchParams.get("MarketplaceIds"), "A1F83G8C2ARO7P");
  assert.equal(seen.searchParams.get("CreatedAfter"), "2026-09-01T00:00:00Z");
  assert.equal(res.structuredContent.orders[0].id, "202-1234567-1234567");
  assert.equal(res.structuredContent.orders[0].currency, "GBP");
});

test("amazon: set_inventory sends a fulfillment_availability merge (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { if (url.href === TOKEN_URL) return tokenOk; seen = { url, init }; return { body: { sku: "SKU-1", status: "ACCEPTED", submissionId: "f1" } }; });
  const res = await client.callTool({ name: "set_inventory", arguments: { sku: "SKU-1", quantity: 20 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "ACCEPTED");
  assert.equal(seen.init.method, "PATCH");
  assert.equal(seen.url.origin + seen.url.pathname, `${HOST}/listings/2021-08-01/items/A2SELLER/SKU-1`);
  assert.deepEqual(JSON.parse(seen.init.body), { productType: "PRODUCT", patches: [{ op: "merge", path: "/attributes/fulfillment_availability", value: [{ fulfillment_channel_code: "DEFAULT", quantity: 20 }] }] });
});

test("amazon: denied access is an auth_error without secrets (wire)", async () => {
  const client = await connect((url) => (url.href === TOKEN_URL ? tokenOk : { status: 403, body: { errors: [{ code: "Unauthorized", message: "Access to requested resource is denied." }] } }));
  const res = await client.callTool({ name: "end_listing", arguments: { listing_id: "SKU-1" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  const text = JSON.stringify(res);
  assert.ok(!text.includes("REFRESHsecretVALUE") && !text.includes("SECRETvalue") && !text.includes("Atza|ACCESS"));
});
