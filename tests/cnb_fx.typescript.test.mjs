import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("market_data", "cnb_fx");
const TEXT = "Datum|1 AUD|1 EUR|100 JPY|1 USD\n02.01.2026|13,797|24,170|13,141|20,611\n05.01.2026|13,835|24,195|13,226|20,742\nDatum|1 AUD|1 EUR|100 JPY|1 USD|1 ZAR\n06.01.2026|13,900|24,200|13,300|20,800|1,250\n";

test("cnb pipe-separated text/plain with decimal commas and DD.MM.YYYY dates (wire)", async () => {
  const { call, log } = await connect(SPEC, () => ({ body: TEXT, type: "text/plain;charset=UTF-8" }));
  const pts = (await call("get_series", { series_id: "100 JPY", start: "2026-01-01" })).structuredContent.points;
  assert.deepEqual(pts.map((p) => [p.time, p.value]), [["2026-01-02", 13.141], ["2026-01-05", 13.226], ["2026-01-06", 13.3]]);
  assert.equal(log[0].url.searchParams.get("rok"), "2026");
  assert.deepEqual((await call("get_series", { series_id: "1 NOPE" })).structuredContent.points, []);
});
