import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("trading", "upbit");

test("upbit: korean-name filter, ticker list, candle path by interval (wire)", async () => {
  const { call, log } = await connect(SPEC, (u) => {
    if (u.pathname === "/v1/market/all") return { body: [{ market: "KRW-BTC", korean_name: "비트코인", english_name: "Bitcoin" }, { market: "KRW-ETH", korean_name: "이더리움", english_name: "Ethereum" }] };
    if (u.pathname === "/v1/ticker") return u.searchParams.get("markets") === "KRW-BTC" ? { body: [{ market: "KRW-BTC", trade_price: 114386000.0, acc_trade_volume_24h: 1060.4 }] } : { status: 404, body: { error: { name: 404, message: "Code not found" } } };
    return { body: [{ market: "KRW-BTC", candle_date_time_utc: "2026-10-01T11:00:00", opening_price: 1.0, high_price: 2.0, low_price: 0.5, trade_price: 1.5, candle_acc_trade_volume: 21.5 }] };
  });
  assert.deepEqual((await call("list_markets", { query: "비트코인" })).structuredContent.markets.map((m) => m.symbol), ["KRW-BTC"]);
  const t = (await call("get_ticker", { symbol: "KRW-BTC" })).structuredContent;
  assert.deepEqual([t.symbol, t.last, t.volume], ["KRW-BTC", 114386000, 1060.4]);
  const c = (await call("get_candles", { symbol: "KRW-BTC", interval: "1h", limit: 2 })).structuredContent.candles;
  assert.equal(c[0].time, "2026-10-01T11:00:00Z");
  assert.equal(log[2].url.pathname, "/v1/candles/minutes/60");
  assert.equal((await call("get_ticker", { symbol: "KRW-NOPE" })).structuredContent.error, "not_found");
  assert.equal((await call("get_candles", { symbol: "KRW-BTC", interval: "2h" })).structuredContent.error, "invalid_input");
});
