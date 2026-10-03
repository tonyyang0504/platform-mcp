import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("competitions", "ctftime");

test("ctftime standings keyed by event id and an HTML 404 summarised (wire)", async () => {
  const { call } = await connect(SPEC, (u) => {
    if (u.pathname === "/api/v1/results/") return { body: { 3335: { title: "Junior.Crypt", scores: [{ team_id: 439893, points: "12793.0000", place: 1 }, { team_id: 431218, points: "12274.5000", place: 2 }] } } };
    return { status: 404, body: '<!DOCTYPE html>\n<html lang="en"><head><title>CTFtime.org / All about CTF / 404</title></head><body>...</body></html>', type: "text/html" };
  });
  const s = (await call("standings", { competition_id: "3335", limit: 1 })).structuredContent;
  assert.deepEqual([s.standings[0].rank, s.standings[0].team, s.standings[0].score, s.next_page], [1, "439893", 12793, 2]);
  const bad = (await call("get_competition", { competition_id: "99999999" })).structuredContent;
  assert.equal(bad.message, "not found (404): HTML page: CTFtime.org / All about CTF / 404");
});
