import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("market_data", "us_treasury_fiscaldata");

test("treasury filter with fmt optional groups (wire)", async () => {
  const { call, log } = await connect(SPEC, () => ({ body: { data: [{ record_date: "2026-07-31", security_desc: "Treasury Bills", avg_interest_rate_amt: "3.758" }] } }));
  const pts = (await call("get_series", { series_id: "Treasury Bills", start: "2026-07-01" })).structuredContent.points;
  assert.deepEqual([pts[0].time, pts[0].value], ["2026-07-31", 3.758]);
  assert.equal(log[0].url.searchParams.get("filter"), "security_desc:eq:Treasury Bills,record_date:gte:2026-07-01");
  await call("get_series", { series_id: "Treasury Bills" });
  assert.equal(log[1].url.searchParams.get("filter"), "security_desc:eq:Treasury Bills");
  await call("get_series", { series_id: "{start}", end: "2026-08-31" });
  assert.equal(log[2].url.searchParams.get("filter"), "security_desc:eq:{start},record_date:lte:2026-08-31"); // a value with braces is not expanded again
  const bad = await call("get_series", { series_id: "Treasury Bills", start: "2026-07-01,security_desc:eq:x" });
  assert.equal(bad.structuredContent.error, "invalid_input"); assert.equal(log.length, 3);
});
