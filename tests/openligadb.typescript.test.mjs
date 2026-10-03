import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("competitions", "openligadb");

test("openligadb leagues (umlauts in the filter) and a table by shortcut/season (wire)", async () => {
  const { call, log } = await connect(SPEC, (u) => (u.pathname === "/getavailableleagues"
    ? { body: [{ leagueName: "1. Fußball-Bundesliga 2025/2026", leagueShortcut: "bl1", leagueSeason: "2025", sport: { sportName: "Fußball" } }, { leagueName: "Handball-Bundesliga", leagueShortcut: "hbl", leagueSeason: "2025", sport: { sportName: "Handball" } }] }
    : { body: [{ teamName: "FC Bayern München", points: 89, matches: 34 }] }));
  assert.deepEqual((await call("discover", { query: "fußball" })).structuredContent.competitions.map((c) => c.id), ["bl1/2025"]);
  const s = (await call("standings", { competition_id: "bl1/2025" })).structuredContent.standings;
  assert.deepEqual([s[0].team, s[0].score], ["FC Bayern München", 89]);
  assert.equal(log[1].url.pathname, "/getbltable/bl1/2025");
});
