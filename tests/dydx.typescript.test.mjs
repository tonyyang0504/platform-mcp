import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("trading", "dydx");
const MKTS = { markets: { "ETH-USD": { ticker: "ETH-USD", oraclePrice: "2707.45", volume24H: "45248782.5", marketType: "CROSS" }, "BTC-USD": { ticker: "BTC-USD", oraclePrice: "83951.4565", volume24H: "5587345.2", marketType: "CROSS" } } };

test("dydx markets keyed by ticker, ticker via markets.* (wire)", async () => {
  const { call } = await connect(SPEC, (u) => {
    const t = u.searchParams.get("ticker");
    if (u.pathname.endsWith("/perpetualMarkets")) return { body: t ? { markets: Object.fromEntries(Object.entries(MKTS.markets).filter(([k]) => k === t)) } : MKTS };
    return { body: { candles: [{ startedAt: "2026-10-01T11:00:00.000Z", open: "83979", high: "83979", low: "83740", close: "83910", baseTokenVolume: "0.1581" }] } };
  });
  assert.deepEqual((await call("list_markets", {})).structuredContent.markets.map((m) => m.symbol), ["BTC-USD", "ETH-USD"]);
  const t = (await call("get_ticker", { symbol: "BTC-USD" })).structuredContent;
  assert.deepEqual([t.symbol, t.last, t.volume], ["BTC-USD", 83951.4565, 5587345.2]);
  assert.equal((await call("get_ticker", { symbol: "ZZZ-USD" })).structuredContent.error, "not_found");
  assert.equal((await call("get_candles", { symbol: "BTC-USD", interval: "1h", limit: 1 })).structuredContent.candles[0].close, 83910);
});
