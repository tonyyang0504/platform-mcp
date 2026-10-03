import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/market_data/bybit_collector.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, {}, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("bybit_collector: public read verbs only (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_candles", "me", "search_symbols"]);
  assert.ok(tools.every((t) => t.annotations.readOnlyHint === true));
  assert.deepEqual(tools.find((t) => t.name === "get_candles").inputSchema.required, ["symbol", "interval"]);
});

test("bybit_collector: get_candles maps result.list positional rows and fixes category=linear (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { retCode: 0, retMsg: "OK", result: { category: "linear", symbol: "BTCUSDT", list: [["1670608800000", "17071", "17073", "17027", "17055.5", "268611", "15.74462667"]] } } }; });
  const res = await client.callTool({ name: "get_candles", arguments: { symbol: "BTCUSDT", interval: "60", limit: 1 } });
  assert.equal(res.isError, false);
  const c = res.structuredContent.candles[0];
  assert.equal(c.time, "1670608800000");
  assert.equal(c.open, 17071);
  assert.equal(c.high, 17073);
  assert.equal(c.low, 17027);
  assert.equal(c.close, 17055.5);
  assert.equal(c.volume, 268611);
  assert.deepEqual(c.raw.values[6], "15.74462667");
  assert.equal(seen.pathname, "/v5/market/kline");
  assert.equal(seen.searchParams.get("category"), "linear");
  assert.equal(seen.searchParams.get("interval"), "60");
  assert.equal(seen.searchParams.get("limit"), "1");
});

test("bybit_collector: search_symbols lists linear instruments by exact symbol (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { retCode: 0, retMsg: "OK", result: { category: "linear", list: [{ symbol: "BTCUSDT", contractType: "LinearPerpetual", status: "Trading", baseCoin: "BTC", quoteCoin: "USDT" }], nextPageCursor: "" } } }; });
  const res = await client.callTool({ name: "search_symbols", arguments: { query: "BTCUSDT" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.results[0].symbol, "BTCUSDT");
  assert.equal(res.structuredContent.results[0].name, "BTC");
  assert.equal(res.structuredContent.results[0].type, "LinearPerpetual");
  assert.equal(seen.pathname, "/v5/market/instruments-info");
  assert.equal(seen.searchParams.get("category"), "linear");
  assert.equal(seen.searchParams.get("symbol"), "BTCUSDT");
});

test("bybit_collector: 403 'access too frequent' is an isError result (wire)", async () => {
  const client = await connect(() => ({ status: 403, body: { retCode: 403, retMsg: "access too frequent" } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
});
