import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("trading", "kucoin");

test("kucoin: null rule matches explicit nulls only; o-c-h-l candles; envelope failure (wire)", async () => {
  const { call, log } = await connect(SPEC, (u) => {
    if (u.pathname === "/api/v2/symbols") return { body: { code: "200000", data: [{ symbol: "ETH-USDT", baseCurrency: "ETH", quoteCurrency: "USDT" }, { symbol: "BTC-USDT", baseCurrency: "BTC", quoteCurrency: "USDT" }] } };
    if (u.pathname === "/api/v1/market/stats") return { body: { code: "200000", data: { symbol: "NOPE-USDT", buy: null, sell: null, vol: null, last: null } } };
    if (u.searchParams.get("symbol") === "BTC-USDT") return { body: { code: "200000", data: [["1790852400", "83965.5", "83989.1", "84033.1", "83788.2", "51.2", "4296825.9"]] } };
    return { body: { msg: "Unsupported trading pair.", code: "400100" } };
  });
  const m = await call("list_markets", { limit: 5 });
  assert.equal(m.isError, false);
  assert.deepEqual(m.structuredContent.markets.map((x) => x.symbol), ["BTC-USDT", "ETH-USDT"]);
  const t = await call("get_ticker", { symbol: "NOPE-USDT" });
  assert.equal(t.structuredContent.error, "not_found"); assert.equal(t.structuredContent.message, "data.last is null");
  const c = (await call("get_candles", { symbol: "BTC-USDT", interval: "1h", limit: 1 })).structuredContent.candles;
  assert.deepEqual([c[0].time, c[0].open, c[0].close, c[0].high, c[0].low], ["2026-10-01T11:00:00Z", 83965.5, 83989.1, 84033.1, 83788.2]);
  assert.equal(log[2].url.searchParams.get("type"), "1hour");
  const bad = await call("get_candles", { symbol: "NOPE-USDT", interval: "1h" });
  assert.equal(bad.structuredContent.error, "not_found");
});
