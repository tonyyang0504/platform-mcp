import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/trading/bitstamp.json", import.meta.url), "utf8"));
const resp = (status, body, type = "application/json") => ({ status, headers: { get: (k) => (k.toLowerCase() === "content-type" && body !== undefined ? type : null) }, text: async () => (body === undefined ? "" : typeof body === "string" ? body : JSON.stringify(body)) });

async function connect(creds, handler) {
  const log = [];
  const fetcher = async (url, init) => { log.push({ url: new URL(url), init }); const r = handler(new URL(url), init, log.length); return resp(r.status ?? 200, r.body, r.type); };
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...creds }, 50, "test", fetcher, a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return { client, log };
}

const m = (sym, base, quote) => ({ name: `${base}/${quote}`, market_symbol: sym, base_currency: base, counter_currency: quote, trading: "Enabled", market_type: "SPOT" });
const MARKETS = [m("eurusd", "EUR", "USD"), m("btcusd", "BTC", "USD"), m("aaveeur", "AAVE", "EUR")];

test("bitstamp exposes the public reads only", async () => {
  const { client } = await connect({}, () => ({ body: [] }));
  const names = (await client.listTools()).tools.map((t) => t.name).sort();
  assert.deepEqual(names, ["get_candles", "get_ticker", "list_markets"]);
});

test("bitstamp list_markets sorts and pages locally (wire)", async () => {
  const { client, log } = await connect({}, () => ({ body: MARKETS }));
  const p1 = (await client.callTool({ name: "list_markets", arguments: { limit: 2 } })).structuredContent;
  assert.deepEqual(p1.markets.map((x) => x.symbol), ["aaveeur", "btcusd"]);
  assert.deepEqual([p1.markets[1].base, p1.markets[1].quote, p1.markets[1].type], ["BTC", "USD", "SPOT"]);
  assert.equal(p1.total, 3);
  assert.equal(p1.next_page, 2);
  const p2 = (await client.callTool({ name: "list_markets", arguments: { limit: 2, page: 2 } })).structuredContent;
  assert.deepEqual(p2.markets.map((x) => x.symbol), ["eurusd"]);
  assert.equal(p2.next_page, null);
  assert.equal(log[0].url.pathname, "/api/v2/markets/");
});

test("bitstamp get_ticker and get_candles (wire)", async () => {
  const { client, log } = await connect({}, (u) => (u.pathname.startsWith("/api/v2/ohlc/")
    ? { body: { data: { pair: "BTC/USD", ohlc: [
      { timestamp: "1790506800", open: "84858.10", high: "84934.09", low: "84819.11", close: "84878.71", volume: "8.50015357" },
      { timestamp: "1790510400", open: "84878.71", high: "85016.81", low: "84794.32", close: "84794.68", volume: "21.85591219" }] } } }
    : { body: { timestamp: "1790515990", last: "85052.34", bid: "85052.33", ask: "85052.34", volume: "591.21243491", market_type: "SPOT" } }));
  const c = (await client.callTool({ name: "get_candles", arguments: { symbol: "btcusd", interval: "1h", limit: 2 } })).structuredContent;
  assert.deepEqual([c.candles[0].time, c.candles[0].open, c.candles[1].close, c.candles[0].volume], ["2026-09-27T11:00:00Z", 84858.1, 84794.68, 8.50015357]);
  assert.equal(log[0].url.pathname, "/api/v2/ohlc/btcusd/");
  const q = log[0].url.searchParams;
  assert.deepEqual([q.get("step"), q.get("limit")], ["3600", "2"]);
  const t = (await client.callTool({ name: "get_ticker", arguments: { symbol: "btcusd" } })).structuredContent;
  assert.deepEqual([t.symbol, t.last, t.bid, t.ask, t.volume], ["btcusd", 85052.34, 85052.33, 85052.34, 591.21243491]);
  assert.equal(log[1].url.pathname, "/api/v2/ticker/btcusd/");
});

test("bitstamp unknown market is a clean tool error", async () => {
  const { client } = await connect({}, () => ({ status: 404, body: "Not found", type: "text/html" }));
  const r = await client.callTool({ name: "get_ticker", arguments: { symbol: "nosuchpair" } });
  assert.equal(r.isError, true);
  assert.equal(r.structuredContent.error, "not_found");
});
