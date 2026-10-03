import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("trading", "gemini");

test("gemini symbols list of strings, ticker volume.*, candles capped (wire)", async () => {
  const rows = Array.from({ length: 50 }, (_, i) => [1790848800000 - 3600000 * i, 1.5, 2, 1, 1.75, 0.5]);
  const { call, log } = await connect(SPEC, (u) => {
    if (u.pathname === "/v1/symbols") return { body: ["ethusd", "btcusd", "btceur", "solusd"] };
    if (u.pathname === "/v1/pubticker/btcusd") return { body: { bid: "83951.63000", ask: "83951.64000", last: "83962.95000", volume: { BTC: "145.5977532", USD: "1", timestamp: 1 } } };
    if (u.pathname === "/v2/candles/btcusd/1hr") return { body: rows };
    return { status: 404, body: { result: "error", reason: "InvalidSymbol", message: "'nopeusd' does not have available data yet" } };
  });
  const m = (await call("list_markets", { query: "btc", limit: 1 })).structuredContent;
  assert.deepEqual(m.markets, [{ symbol: "btceur", raw: { values: "btceur" } }]);
  assert.equal(m.total, 2);
  const t = (await call("get_ticker", { symbol: "btcusd" })).structuredContent;
  assert.deepEqual([t.symbol, t.last, t.volume], ["btcusd", 83962.95, 145.5977532]);
  const c = (await call("get_candles", { symbol: "btcusd", interval: "1hr", limit: 3 })).structuredContent.candles;
  assert.equal(c.length, 3); assert.equal(c[0].time, "2026-10-01T10:00:00Z");
  const bad = await call("get_ticker", { symbol: "nopeusd" });
  assert.equal(bad.structuredContent.error, "not_found");
  assert.equal(log[2].url.pathname, "/v2/candles/btcusd/1hr");
});
