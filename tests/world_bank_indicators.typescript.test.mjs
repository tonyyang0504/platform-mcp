import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("market_data", "world_bank_indicators");

test("world bank [meta, rows], part: series id and 200 error arrays (wire)", async () => {
  const { call, log } = await connect(SPEC, (u) => (u.pathname.endsWith("/NY.GDP.MKTP.CD")
    ? { body: [{ page: 1, total: 2 }, [{ date: "2024", value: 29298013000000 }, { date: "2023", value: null }]] }
    : { body: [{ message: [{ id: "120", key: "Invalid value", value: "The provided parameter value is not valid" }] }] }));
  const pts = (await call("get_series", { series_id: "USA/NY.GDP.MKTP.CD", start: "2023-01-01", end: "2024-12-31" })).structuredContent.points;
  assert.deepEqual(pts.map((p) => [p.time, p.value]), [["2024", 29298013000000], ["2023", null]]);
  assert.equal(log[0].url.pathname, "/v2/country/USA/indicator/NY.GDP.MKTP.CD");
  assert.equal(log[0].url.searchParams.get("date"), "2023:2024");
  const bad = (await call("get_series", { series_id: "USA/NOPE.X" })).structuredContent;
  assert.deepEqual([bad.error, bad.message], ["invalid_input", "The provided parameter value is not valid"]);
  assert.equal((await call("get_series", { series_id: "USA" })).structuredContent.error, "invalid_input");
});
