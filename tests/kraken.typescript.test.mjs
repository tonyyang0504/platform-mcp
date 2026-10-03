import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("trading", "kraken");
const PAIRS = { error: [], result: {
  XXBTZUSD: { altname: "XBTUSD", wsname: "XBT/USD", aclass_base: "currency", base: "XXBT", quote: "ZUSD" },
  XETHZEUR: { altname: "ETHEUR", wsname: "ETH/EUR", aclass_base: "currency", base: "XETH", quote: "ZEUR" },
  AAVEXBT: { altname: "AAVEXBT", wsname: "AAVE/XBT", aclass_base: "currency", base: "AAVE", quote: "XXBT" } } };

test("kraken list_markets: values of the keyed result, filtered and sorted (wire)", async () => {
  const { call } = await connect(SPEC, () => ({ body: PAIRS }));
  const r = (await call("list_markets", { query: "xbt", limit: 1 })).structuredContent;
  assert.deepEqual(r.markets.map((m) => m.symbol), ["AAVEXBT"]);
  assert.equal(r.total, 2); assert.equal(r.next_page, 2);
});

test("kraken ticker reads result.* and candles keep the newest limit (wire)", async () => {
  const rows = Array.from({ length: 720 }, (_, i) => [1788260400 + 3600 * i, "1.0", "2.0", "0.5", String(i), "1.1", "10.5", 3]);
  const { call, log } = await connect(SPEC, (u) => (u.pathname.endsWith("/Ticker")
    ? { body: { error: [], result: { XXBTZUSD: { a: ["83927.90000", "1", "1.000"], b: ["83927.80000", "1", "1.000"], c: ["83927.10000", "0.0001"], v: ["1175.2", "3280.5"] } } } }
    : { body: { error: [], result: { XXBTZUSD: rows, last: 1 } } }));
  const t = (await call("get_ticker", { symbol: "XBTUSD" })).structuredContent;
  assert.deepEqual([t.symbol, t.last, t.bid, t.ask, t.volume], ["XBTUSD", 83927.1, 83927.8, 83927.9, 3280.5]);
  const c = (await call("get_candles", { symbol: "XBTUSD", interval: "1h", limit: 2 })).structuredContent.candles;
  assert.deepEqual(c.map((x) => x.close), [718, 719]);
  assert.equal(c[0].time, "2026-10-01T09:00:00Z");
  assert.equal(log[1].url.searchParams.get("interval"), "60");
});

test("kraken error list is a not_found tool error (wire)", async () => {
  const { call } = await connect(SPEC, () => ({ body: { error: ["EQuery:Unknown asset pair"] } }));
  const r = await call("get_ticker", { symbol: "NOPEUSD" });
  assert.equal(r.isError, true);
  assert.equal(r.structuredContent.error, "not_found");
  assert.match(r.structuredContent.message, /Unknown asset pair/);
});
