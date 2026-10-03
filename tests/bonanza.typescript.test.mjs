import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/bonanza.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null) }, text: async () => JSON.stringify(r.body ?? {}) }; };

process.env.PLATFORM_MCP_BONANZA_DEV_ID = "DEVID-123456";
process.env.PLATFORM_MCP_BONANZA_CERT_ID = "CERTID-abcdef";
process.env.PLATFORM_MCP_BONANZA_AUTH_TOKEN = "USERTOKEN-secret99";

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("bonanza: dev/cert headers and token inside the request envelope (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { ack: "Success", getTokenStatusResponse: { verified: true } } }; });
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, false);
  assert.equal(seen.url.href, "https://api.bonanza.com/api_requests/secure_request");
  assert.equal(seen.init.headers["X-BONANZLE-API-DEV-NAME"], "DEVID-123456");
  assert.deepEqual(JSON.parse(seen.init.body), { getTokenStatusRequest: { requesterCredentials: { bonanzleAuthToken: "USERTOKEN-secret99" } } });
});

test("bonanza: list_orders unwraps orderArray[].order (wire)", async () => {
  const client = await connect(() => ({ body: { ack: "Success", getOrdersResponse: { orderArray: [{ order: { orderID: 1811, orderStatus: "Shipped", total: "104.32" } }], paginationResult: { totalNumberOfEntries: 1 } } } }));
  const res = await client.callTool({ name: "list_orders", arguments: {} });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.orders[0].id, "1811");
  assert.equal(res.structuredContent.orders[0].status, "Shipped");
  assert.equal(res.structuredContent.total, 1);
});

test("bonanza: ack Failure is an error and the token is scrubbed (wire)", async () => {
  const client = await connect(() => ({ body: { ack: "Failure", errorMessage: { error: [{ type: "InvalidAuthToken", message: "bad USERTOKEN-secret99" }] } } }));
  const res = await client.callTool({ name: "end_listing", arguments: { listing_id: "205172" } });
  assert.equal(res.isError, true);
  assert.ok(!JSON.stringify(res).includes("USERTOKEN-secret99"));
});
