import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/walmart.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null) }, text: async () => JSON.stringify(r.body ?? {}) }; };

process.env.PLATFORM_MCP_WALMART_CLIENT_ID = "CID-wm";
process.env.PLATFORM_MCP_WALMART_CLIENT_SECRET = "SECRET-wm-1";

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

const hdr = (init, name) => { const h = init.headers ?? {}; const k = Object.keys(h).find((x) => x.toLowerCase() === name.toLowerCase()); return k ? h[k] : undefined; };

test("walmart: token with WM headers, then WM_SEC.ACCESS_TOKEN and a fresh correlation id per call (wire)", async () => {
  const log = [];
  const client = await connect((url, init) => {
    log.push({ url, init });
    if (url.pathname === "/v3/token") return { body: { access_token: "ACCESS-wm", token_type: "Bearer", expires_in: 900 } };
    return { body: { list: { meta: { totalCount: 1 }, elements: { order: [{ purchaseOrderId: "1796277083022", customerOrderId: "5281956426648" }] } } } };
  });
  const res = await client.callTool({ name: "list_orders", arguments: { since: "2026-09-01" } });
  assert.equal(res.isError, false);
  assert.deepEqual(res.structuredContent.orders.map((o) => o.id), ["1796277083022"]);
  await client.callTool({ name: "list_orders", arguments: {} });
  const tok = log.find((x) => x.url.pathname === "/v3/token");
  assert.equal(hdr(tok.init, "WM_SVC.NAME"), "Walmart Marketplace");
  assert.match(hdr(tok.init, "WM_QOS.CORRELATION_ID"), /^platform-mcp-\d+$/);
  assert.equal(hdr(tok.init, "Authorization"), "Basic " + Buffer.from("CID-wm:SECRET-wm-1").toString("base64"));
  const calls = log.filter((x) => x.url.pathname === "/v3/orders");
  assert.equal(calls.length, 2);
  assert.equal(calls[0].url.searchParams.get("createdStartDate"), "2026-09-01");
  for (const c of calls) {
    assert.equal(hdr(c.init, "WM_SEC.ACCESS_TOKEN"), "ACCESS-wm");
    assert.equal(hdr(c.init, "WM_SVC.NAME"), "Walmart Marketplace");
    assert.match(hdr(c.init, "WM_QOS.CORRELATION_ID"), /^[0-9a-f]{32}$/);
  }
  assert.notEqual(hdr(calls[0].init, "WM_QOS.CORRELATION_ID"), hdr(calls[1].init, "WM_QOS.CORRELATION_ID"));
});

test("walmart: update_listing PUTs a BASE USD price (wire)", async () => {
  let seen;
  const client = await connect((url, init) => {
    if (url.pathname === "/v3/token") return { body: { access_token: "ACCESS-wm", expires_in: 900 } };
    seen = { url, init };
    return { body: { ItemPriceResponse: { sku: "97964_KFTest", message: "ok" } } };
  });
  const res = await client.callTool({ name: "update_listing", arguments: { listing_id: "97964_KFTest", price: 12.5 } });
  assert.equal(res.isError, false);
  assert.equal(seen.init.method, "PUT");
  assert.deepEqual(JSON.parse(seen.init.body), { sku: "97964_KFTest", pricing: [{ currentPriceType: "BASE", currentPrice: { currency: "USD", amount: 12.5 } }] });
});

test("walmart: 400 on retire is an error (wire)", async () => {
  const client = await connect((url) => (url.pathname === "/v3/token" ? { body: { access_token: "ACCESS-wm", expires_in: 900 } } : { status: 400, body: { errors: [{ code: "INVALID" }] } }));
  const res = await client.callTool({ name: "end_listing", arguments: { listing_id: "SKU-2" } });
  assert.equal(res.isError, true);
});
