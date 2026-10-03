import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("market_data", "nbp_rates");

test("nbp window in the path, Polish names, plain-text 404 (wire)", async () => {
  const { call, log } = await connect(SPEC, (u) => {
    if (u.pathname.endsWith("/tables/A/")) return { body: [{ table: "A", rates: [{ currency: "dolar amerykański", code: "USD", mid: 3.87 }, { currency: "euro", code: "EUR", mid: 4.2 }] }] };
    if (u.pathname.includes("/USD/")) return { body: { table: "A", code: "USD", rates: [{ no: "187/A/NBP/2026", effectiveDate: "2026-09-25", mid: 3.8404 }] } };
    return { status: 404, body: "404 NotFound - Not Found - Brak danych", type: "text/plain" };
  });
  const pts = (await call("get_series", { series_id: "A/USD", start: "2026-09-25", end: "2026-09-30" })).structuredContent.points;
  assert.deepEqual(pts.map((p) => [p.time, p.value]), [["2026-09-25", 3.8404]]);
  assert.equal(log[0].url.pathname, "/api/exchangerates/rates/A/USD/2026-09-25/2026-09-30/");
  const missing = (await call("get_series", { series_id: "A/USD" })).structuredContent;
  assert.equal(missing.error, "invalid_input"); assert.match(missing.message, /date:start/);
  assert.deepEqual((await call("search_symbols", { query: "dolar" })).structuredContent.results.map((x) => x.symbol), ["A/USD"]);
  assert.equal((await call("get_series", { series_id: "A/XXX", start: "2026-09-25", end: "2026-09-30" })).structuredContent.error, "not_found");
});
