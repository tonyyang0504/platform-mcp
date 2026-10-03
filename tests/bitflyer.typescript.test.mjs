import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("trading", "bitflyer");

test("bitflyer markets, ticker and an invalid product (wire)", async () => {
  const { call } = await connect(SPEC, (u) => {
    if (u.pathname === "/v1/getmarkets") return { body: [{ product_code: "ETH_JPY", market_type: "Spot" }, { product_code: "BTC_JPY", market_type: "Spot" }, { product_code: "FX_BTC_JPY", market_type: "FX" }] };
    if (u.searchParams.get("product_code") === "BTC_JPY") return { body: { product_code: "BTC_JPY", best_bid: 13264727.0, best_ask: 13270396.0, ltp: 13265634.0, volume_by_product: 436.6 } };
    return { status: 400, body: { status: -100, error_message: "Invalid product", data: null } };
  });
  assert.deepEqual((await call("list_markets", { query: "btc" })).structuredContent.markets.map((m) => m.symbol), ["BTC_JPY", "FX_BTC_JPY"]);
  const t = (await call("get_ticker", { symbol: "BTC_JPY" })).structuredContent;
  assert.deepEqual([t.last, t.bid, t.ask, t.volume], [13265634, 13264727, 13270396, 436.6]);
  assert.equal((await call("get_ticker", { symbol: "NOPE" })).structuredContent.error, "invalid_input");
});
