import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("market_data", "coinpaprika");

test("coinpaprika follows a same-origin 301, refuses a cross-origin one, fails on HTML (wire)", async () => {
  let mode = "redirect";
  const { call, log } = await connect(SPEC, (u, init) => {
    assert.equal(init.redirect, "manual");
    if (mode === "html") return { body: "<html><body>Just a moment...</body></html>", type: "text/html" };
    if (u.pathname === "/v1/search") return { status: mode === "evil" ? 302 : 301, body: "Moved", type: "text/plain", headers: { location: mode === "evil" ? "https://evil.example/collect" : "/v1/search/?q=bitcoin&c=currencies&limit=2" } };
    return { body: { currencies: [{ id: "btc-bitcoin", name: "Bitcoin", symbol: "BTC", type: "coin" }] } };
  });
  const r = (await call("search_symbols", { query: "bitcoin", limit: 2 })).structuredContent;
  assert.equal(r.results[0].symbol, "btc-bitcoin");
  assert.equal(log[1].url.pathname, "/v1/search/");
  mode = "evil";
  const bad = await call("search_symbols", { query: "x" });
  assert.equal(bad.structuredContent.error, "upstream_error"); assert.match(bad.structuredContent.message, /evil\.example/);
  assert.ok(!log.some((l) => l.url.host === "evil.example"));
  mode = "html";
  const html = await call("search_symbols", { query: "x" });
  assert.equal(html.structuredContent.error, "upstream_error"); assert.match(html.structuredContent.message, /text\/html/);
});
