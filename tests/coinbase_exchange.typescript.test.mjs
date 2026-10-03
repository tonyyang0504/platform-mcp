import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("trading", "coinbase_exchange");

test("coinbase exchange ticker (arg:symbol) and l-h-o-c candles (wire)", async () => {
  const { call, log } = await connect(SPEC, (u) => (u.pathname.endsWith("/ticker")
    ? (u.pathname.includes("NOPE") ? { status: 404, body: { message: "NotFound" } } : { body: { ask: "83942.15", bid: "83942.14", volume: "7070.2", price: "83942.14" } })
    : { body: [[1790852400, 83743.11, 84019, 83935.64, 83985.19, 120.7], [1790848800, 1, 2, 1.5, 1.7, 3]] }));
  const t = (await call("get_ticker", { symbol: "BTC-USD" })).structuredContent;
  assert.deepEqual([t.symbol, t.last, t.ask], ["BTC-USD", 83942.14, 83942.15]);
  const c = (await call("get_candles", { symbol: "BTC-USD", interval: "1h", limit: 1 })).structuredContent.candles;
  assert.deepEqual([c.length, c[0].low, c[0].high, c[0].open, c[0].close], [1, 83743.11, 84019, 83935.64, 83985.19]);
  assert.equal(log[1].url.searchParams.get("granularity"), "3600");
  assert.equal((await call("get_ticker", { symbol: "NOPE-USD" })).structuredContent.error, "not_found");
});
