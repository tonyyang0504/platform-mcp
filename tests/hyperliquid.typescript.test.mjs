import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/trading/hyperliquid.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, {}, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("hyperliquid offers only public read verbs (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_ticker", "list_markets", "list_orders", "me"]);
  assert.ok(tools.every((t) => t.annotations.readOnlyHint === true));
});

test("hyperliquid list_markets posts the literal {type: meta} body and maps the universe (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { universe: [{ name: "BTC", szDecimals: 5, maxLeverage: 50 }], marginTables: [] } }; });
  const res = await client.callTool({ name: "list_markets", arguments: {} });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.markets[0].symbol, "BTC");
  assert.equal(res.structuredContent.next_page, null);
  assert.equal(seen.init.method, "POST");
  assert.deepEqual(JSON.parse(seen.init.body), { type: "meta" });
  assert.equal(seen.init.headers["Content-Type"], "application/json");
});

test("hyperliquid get_ticker reads top of book from l2Book (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = init; return { body: { coin: "BTC", time: 1, levels: [[{ px: "113377.0", sz: "7.6699", n: 17 }], [{ px: "113397.0", sz: "0.11543", n: 3 }]] } }; });
  const res = await client.callTool({ name: "get_ticker", arguments: { symbol: "BTC" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.bid, 113377); // numbers, as the vocabulary types bid/ask
  assert.equal(res.structuredContent.ask, 113397);
  assert.deepEqual(JSON.parse(seen.body), { type: "l2Book", coin: "BTC" });
});

test("hyperliquid list_orders posts openOrders for the configured address (wire)", async () => {
  let seen;
  const fetcher = fakeFetch((url, init) => { seen = init; return { body: [{ coin: "BTC", limitPx: "29792.0", oid: 91490942, side: "A", sz: "0.0", timestamp: 1 }] }; });
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { wallet_address: "0x1111111111111111111111111111111111111111" }, 50, "test", fetcher));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  const res = await client.callTool({ name: "list_orders", arguments: {} });
  assert.equal(res.structuredContent.orders[0].order_id, "91490942");
  assert.deepEqual(JSON.parse(seen.body), { type: "openOrders", user: "0x1111111111111111111111111111111111111111" });
});
