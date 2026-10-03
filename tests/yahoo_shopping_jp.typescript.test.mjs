import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/yahoo_shopping_jp.json", import.meta.url), "utf8"));
const fetcher = (handler) => async (url, init) => { const r = handler(new URL(url), init); const xml = typeof r.text === "string"; return { status: r.status ?? 200, headers: { get: (k) => (k.toLowerCase() === "content-type" ? (xml ? "application/xml" : "application/json") : null) }, text: async () => (xml ? r.text : JSON.stringify(r.body ?? {})) }; };

process.env.PLATFORM_MCP_YAHOO_SHOPPING_JP_CLIENT_ID = "CID-yj";
process.env.PLATFORM_MCP_YAHOO_SHOPPING_JP_CLIENT_SECRET = "SECRET-yj-1";
process.env.PLATFORM_MCP_YAHOO_SHOPPING_JP_REFRESH_TOKEN = "REFRESH-yj-1";
process.env.PLATFORM_MCP_YAHOO_SHOPPING_JP_SELLER_ID = "teststore";

async function connect(handler) {
  globalThis.fetch = fetcher((url, init) => (url.hostname === "auth.login.yahoo.co.jp" ? { body: { access_token: "ACCESS-yj", expires_in: 3600 } } : handler(url, init)));
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("yahoo_shopping_jp: setStock form body with bearer token, XML answer (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { text: '<ResultSet totalResultsAvailable="1"><Result><ItemCode>item-01</ItemCode><SubCode>sub-01</SubCode><Quantity>11</Quantity></Result></ResultSet>' }; });
  const res = await client.callTool({ name: "set_inventory", arguments: { sku: "item-01:sub-01", quantity: 11 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.stock, "11");
  assert.equal(seen.url.pathname, "/ShoppingWebService/V1/setStock");
  assert.equal(seen.init.headers.Authorization, "Bearer ACCESS-yj");
  const form = new URLSearchParams(seen.init.body);
  assert.equal(form.get("seller_id"), "teststore");
  assert.equal(form.get("item_code"), "item-01:sub-01");
  assert.equal(form.get("quantity"), "11");
});

test("yahoo_shopping_jp: updateItems item1 is an encoded key=value string (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = init; return { text: "<ResultSet><Status>OK</Status></ResultSet>" }; });
  const res = await client.callTool({ name: "update_listing", arguments: { listing_id: "abc1", price: 1980 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "OK");
  assert.equal(new URLSearchParams(seen.body).get("item1"), "item_code=abc1&price=1980&sale_price=");
});

test("yahoo_shopping_jp: XML 400 error is an error (wire)", async () => {
  const client = await connect(() => ({ status: 400, text: "<Error><Message>bad</Message><Code>st-02101</Code></Error>" }));
  const res = await client.callTool({ name: "end_listing", arguments: { listing_id: "x" } });
  assert.equal(res.isError, true);
});
