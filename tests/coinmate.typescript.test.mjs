import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("trading", "coinmate");

test("coinmate pairs, ticker and the {error: true} envelope (wire)", async () => {
  const { call } = await connect(SPEC, (u) => {
    if (u.pathname.endsWith("/tradingPairs")) return { body: { error: false, errorMessage: null, data: [{ name: "BTC_EUR", firstCurrency: "BTC", secondCurrency: "EUR" }, { name: "BTC_CZK", firstCurrency: "BTC", secondCurrency: "CZK" }] } };
    return u.searchParams.get("currencyPair") === "BTC_EUR" ? { body: { error: false, errorMessage: null, data: { last: 74236.9, bid: 74236.8, ask: 74236.9, amount: 17.1 } } }
      : { body: { error: true, errorMessage: "Currency pair NOPE_EUR not found.", data: null } };
  });
  assert.deepEqual((await call("list_markets", {})).structuredContent.markets.map((m) => m.symbol), ["BTC_CZK", "BTC_EUR"]);
  assert.equal((await call("get_ticker", { symbol: "BTC_EUR" })).structuredContent.volume, 17.1);
  const bad = (await call("get_ticker", { symbol: "NOPE_EUR" })).structuredContent;
  assert.equal(bad.error, "not_found"); assert.match(bad.message, /NOPE_EUR/);
});
