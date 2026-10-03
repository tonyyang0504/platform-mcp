// Bitvavo contract test (TypeScript twin of test_bitvavo_python.py); responses shaped like the live API.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/trading/bitvavo.json", import.meta.url), "utf8"));
const resp = (status, body) => ({ status, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null) }, text: async () => JSON.stringify(body) });
async function connect(handler) {
  const log = [];
  const fetcher = async (url, init) => { log.push({ url: new URL(url), init }); const r = handler(new URL(url)); return resp(r.status ?? 200, r.body); };
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, {}, 50, "test", fetcher, a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return { client, log };
}
const MARKETS = [
  { market: "FUN-EUR", status: "trading", base: "FUN", quote: "EUR" }, { market: "BTC-EUR", status: "trading", base: "BTC", quote: "EUR" },
  { market: "ETH-USDC", status: "halted", base: "ETH", quote: "USDC" }, { market: "ADA-EUR", status: "trading", base: "ADA", quote: "EUR" }];

test("bitvavo list_markets filters, sorts and pages one download (wire)", async () => {
  const { client, log } = await connect(() => ({ body: MARKETS }));
  const p1 = (await client.callTool({ name: "list_markets", arguments: { limit: 2 } })).structuredContent;
  assert.deepEqual([p1.markets.map((m) => m.symbol), p1.total, p1.next_page, p1.markets[1].type], [["ADA-EUR", "BTC-EUR"], 4, 2, "spot"]);
  const p2 = (await client.callTool({ name: "list_markets", arguments: { limit: 2, page: 2 } })).structuredContent;
  assert.deepEqual([p2.markets.map((m) => m.symbol), p2.next_page], [["ETH-USDC", "FUN-EUR"], null]);
  const q = (await client.callTool({ name: "list_markets", arguments: { query: "usdc" } })).structuredContent;
  assert.deepEqual([q.markets.map((m) => m.symbol), q.total, log.length, log[0].url.pathname], [["ETH-USDC"], 1, 1, "/v2/markets"]);
});

test("bitvavo get_ticker and get_candles map the live shapes (wire)", async () => {
  const { client, log } = await connect((u) => (u.pathname.endsWith("/candles")
    ? { body: [[1790521200000, "74243", "74355", "74081", "74211", "20.99724923"]] }
    : { body: { market: "BTC-EUR", high: "7.479E+4", last: "74206", bid: "74209", ask: "74210", volume: "298.00767161" } }));
  const t = (await client.callTool({ name: "get_ticker", arguments: { symbol: "BTC-EUR" } })).structuredContent;
  assert.deepEqual([t.symbol, t.last, t.bid, t.ask, t.volume], ["BTC-EUR", 74206, 74209, 74210, 298.00767161]);
  assert.equal(log[0].url.searchParams.get("market"), "BTC-EUR");
  const c = (await client.callTool({ name: "get_candles", arguments: { symbol: "BTC-EUR", interval: "1h", limit: 1 } })).structuredContent;
  assert.deepEqual([c.candles[0].time, c.candles[0].open, c.candles[0].volume], ["2026-09-27T15:00:00Z", 74243, 20.99724923]);
  assert.deepEqual([log[1].url.pathname, log[1].url.searchParams.get("interval"), log[1].url.searchParams.get("limit")], ["/v2/BTC-EUR/candles", "1h", "1"]);
});

test("bitvavo unknown market 400 is invalid_input (wire)", async () => {
  const { client } = await connect(() => ({ status: 400, body: { errorCode: 205, error: "market parameter is invalid." } }));
  const r = await client.callTool({ name: "get_ticker", arguments: { symbol: "ZZZ-EUR" } });
  assert.deepEqual([r.isError, r.structuredContent.error, r.structuredContent.http_status], [true, "invalid_input", 400]);
});
