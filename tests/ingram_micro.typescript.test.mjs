import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/ingram_micro.json", import.meta.url), "utf8"));
const CREDS = { client_id: "im-client", client_secret: "im-secret-0123456789", customer_number: "20-222222", country_code: "US" };

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", fakeFetch(handler), a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("ingram_micro: token, account headers and a per-request IM-CorrelationID (wire)", async () => {
  const calls = [];
  const client = await connect((url, init) => {
    calls.push({ url, init });
    if (url.pathname === "/oauth/oauth30/token") return { body: { access_token: "im-access-token-xyz", expires_in: 86399 } };
    return { body: { ingramPartNumber: "5348387", vendorPartNumber: "20VE0117MH", description: "TB 15 G2", vendorName: "Lenovo" } };
  });
  const res = await client.callTool({ name: "get_product", arguments: { id: "5348387" } });
  await client.callTool({ name: "get_product", arguments: { id: "5348387" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "5348387");
  assert.equal(res.structuredContent.sku, "20VE0117MH");
  const [a, b] = calls.filter((c) => c.url.pathname.startsWith("/resellers"));
  assert.equal(a.url.pathname, "/resellers/v6/catalog/details/5348387");
  assert.equal(a.init.headers.Authorization, "Bearer im-access-token-xyz");
  assert.equal(a.init.headers["IM-CustomerNumber"], "20-222222");
  assert.equal(a.init.headers["IM-CountryCode"], "US");
  assert.match(a.init.headers["IM-CorrelationID"], /^[0-9a-f]{32}$/);
  assert.notEqual(a.init.headers["IM-CorrelationID"], b.init.headers["IM-CorrelationID"]);
  assert.equal(calls.filter((c) => c.url.pathname === "/oauth/oauth30/token").length, 1);
});

test("ingram_micro: create_order body shape", async () => {
  let sent;
  const client = await connect((url, init) => {
    if (url.pathname === "/oauth/oauth30/token") return { body: { access_token: "t0k3n-abcdef", expires_in: 86399 } };
    sent = JSON.parse(init.body);
    return { status: 201, body: { purchaseOrderTotal: 14.29, orders: [{ ingramOrderNumber: "20-RFKW4", currencyCode: "USD" }] } };
  });
  const items = [{ customerLineNumber: "1", ingramPartNumber: "DF4128", quantity: 1 }];
  const res = await client.callTool({ name: "create_order", arguments: { items, shipping_address: { city: "LENEXA", countryCode: "US" } } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "20-RFKW4");
  assert.deepEqual(sent.lines, items);
  assert.deepEqual(sent.shipToInfo, { city: "LENEXA", countryCode: "US" });
  assert.match(sent.customerOrderNumber, /^MCP\d{12}$/);
});
