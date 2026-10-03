import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("market_data", "snb_data");
const CSV = '﻿"CubeId";"devkum"\r\n"PublishingDate";"2026-10-01 14:30"\r\n\r\n"Date";"D0";"D1";"Value"\r\n"2026-08";"M0";"EUR1";"0.93629"\r\n"2026-08";"M0";"GBP1";"1.09363"\r\n"2026-08";"M1";"EUR1";"0.9301"\r\n"2026-09";"M0";"EUR1";\r\n"2026-09";"M0";"GBP1";"1.1"\r\n';

test("snb long-format semicolon CSV with a preamble, filtered to one series (wire)", async () => {
  const { call, log } = await connect(SPEC, () => ({ body: CSV, type: "text/csv;charset=UTF-8" }));
  const pts = (await call("get_series", { series_id: "devkum/M0/EUR1", start: "2026-08-01" })).structuredContent.points;
  assert.deepEqual(pts.map((p) => [p.time, p.value]), [["2026-08", 0.93629]]);
  assert.equal(log[0].url.pathname, "/api/cube/devkum/data/csv/en");
  assert.equal(log[0].url.searchParams.get("fromDate"), "2026-08");
  assert.deepEqual((await call("get_series", { series_id: "devkum/M0/GBP1" })).structuredContent.points.map((p) => p.value), [1.09363, 1.1]);
});
