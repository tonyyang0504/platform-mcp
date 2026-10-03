import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("trading", "kalshi");

test("kalshi markets by cursor and a market ticker (wire)", async () => {
  const { call, log } = await connect(SPEC, (u) => {
    if (u.pathname.endsWith("/markets")) return u.searchParams.get("cursor") === "abc"
      ? { body: { cursor: "", markets: [{ ticker: "KXB-1", event_ticker: "KXB", market_type: "binary" }] } }
      : { body: { cursor: "abc", markets: [{ ticker: "KXA-1", event_ticker: "KXA", market_type: "binary" }] } };
    if (u.pathname.endsWith("/KXA-1")) return { body: { market: { ticker: "KXA-1", last_price_dollars: "0.4200", yes_bid_dollars: "0.4100", yes_ask_dollars: "0.4300", volume_24h_fp: "12.00" } } };
    return { status: 404, body: { error: { code: "not_found", message: "not found" } } };
  });
  const p1 = (await call("list_markets", { limit: 1 })).structuredContent;
  assert.deepEqual([p1.markets[0].symbol, p1.next_cursor, p1.next_page], ["KXA-1", "abc", null]);
  assert.equal(log[0].url.searchParams.get("mve_filter"), "exclude");
  const p2 = (await call("list_markets", { limit: 1, cursor: "abc" })).structuredContent;
  assert.deepEqual([p2.markets[0].symbol, p2.next_cursor], ["KXB-1", null]);
  const t = (await call("get_ticker", { symbol: "KXA-1" })).structuredContent;
  assert.deepEqual([t.last, t.bid, t.ask, t.volume], [0.42, 0.41, 0.43, 12]);
  assert.equal((await call("get_ticker", { symbol: "NOPE" })).structuredContent.error, "not_found");
});
