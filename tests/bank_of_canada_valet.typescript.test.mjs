import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("market_data", "bank_of_canada_valet");

test("valet observations keyed by the series name and the series list (wire)", async () => {
  const { call } = await connect(SPEC, (u) => {
    if (u.pathname.endsWith("/lists/series/json")) return { body: { series: { FXUSDCAD: { label: "USD/CAD", description: "Daily average exchange rate of the US dollar in Canadian dollars." }, "A.AGRI": { label: "Annual BCPI Agriculture", description: "x" } } } };
    if (u.pathname.includes("/FXUSDCAD/")) return { body: { observations: [{ d: "2026-09-25", FXUSDCAD: { v: "1.4145" } }] } };
    return { status: 404, body: { message: "Series NOPEX not found." } };
  });
  const pts = (await call("get_series", { series_id: "FXUSDCAD" })).structuredContent.points;
  assert.deepEqual([pts[0].time, pts[0].value], ["2026-09-25", 1.4145]);
  assert.deepEqual((await call("search_symbols", { query: "us dollar" })).structuredContent.results.map((x) => x.symbol), ["FXUSDCAD"]);
  assert.equal((await call("get_series", { series_id: "NOPEX" })).structuredContent.error, "not_found");
});
