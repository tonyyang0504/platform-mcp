import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("trading", "mexc");

test("mexc markets, ticker and klines with the 60m interval (wire)", async () => {
  const { call, log } = await connect(SPEC, (u) => {
    if (u.pathname === "/api/v3/exchangeInfo") return { body: { symbols: [{ symbol: "ETHUSDT", baseAsset: "ETH", quoteAsset: "USDT", fullName: "Ethereum" }, { symbol: "BTCUSDT", baseAsset: "BTC", quoteAsset: "USDT", fullName: "Bitcoin" }] } };
    if (u.pathname === "/api/v3/ticker/24hr") return u.searchParams.get("symbol") === "BTCUSDT" ? { body: { symbol: "BTCUSDT", lastPrice: "83954.13", bidPrice: "83954.1", askPrice: "83954.2", volume: "1234.5" } } : { status: 400, body: { msg: "invalid symbol", code: -1121 } };
    return { body: [[1790848800000, "83779.12", "84075.96", "83412.21", "83954.13", "235.3", 1790852400000, "19711510.36"]] };
  });
  assert.deepEqual((await call("list_markets", { query: "bitcoin" })).structuredContent.markets.map((m) => m.symbol), ["BTCUSDT"]);
  const t = (await call("get_ticker", { symbol: "BTCUSDT" })).structuredContent;
  assert.deepEqual([t.last, t.bid, t.ask, t.volume], [83954.13, 83954.1, 83954.2, 1234.5]);
  const c = (await call("get_candles", { symbol: "BTCUSDT", interval: "1h", limit: 1 })).structuredContent.candles;
  assert.equal(c[0].time, "2026-10-01T10:00:00Z");
  assert.equal(log[2].url.searchParams.get("interval"), "60m");
  assert.equal((await call("get_ticker", { symbol: "NOPEUSDT" })).structuredContent.error, "invalid_input");
});
