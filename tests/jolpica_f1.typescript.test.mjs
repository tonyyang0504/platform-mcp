import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("competitions", "jolpica_f1");
const RACE = { season: "2026", round: "5", raceName: "Canadian Grand Prix", date: "2026-05-24", time: "20:00:00Z", Circuit: { circuitName: "Circuit Gilles Villeneuve", Location: { locality: "Montreal", country: "Canada" } } };

test("jolpica string totals, season/round ids, results (wire)", async () => {
  const { call, log } = await connect(SPEC, (u) => {
    if (u.pathname.endsWith("/current/races.json")) return { body: { MRData: { total: "23", RaceTable: { Races: [RACE, { ...RACE, round: "6" }] } } } };
    if (u.pathname.endsWith("/2026/5/results.json")) return { body: { MRData: { total: "22", RaceTable: { Races: [{ ...RACE, Results: [{ position: "1", points: "25", Driver: { givenName: "Andrea Kimi", familyName: "Antonelli" }, Constructor: { name: "Mercedes" } }] }] } } } };
    return { body: { MRData: { total: "0", RaceTable: { Races: [] } } } };
  });
  const r = (await call("discover", { limit: 2, page: 2 })).structuredContent;
  assert.deepEqual([r.competitions.map((c) => c.id), r.total, r.next_page], [["2026/5", "2026/6"], 23, 3]);
  assert.equal(log[0].url.searchParams.get("offset"), "2");
  const s = (await call("standings", { competition_id: "2026/5", limit: 1 })).structuredContent;
  assert.deepEqual([s.standings[0].team, s.standings[0].rank, s.total], ["Andrea Kimi Antonelli (Mercedes)", 1, 22]);
  assert.equal(log[1].url.pathname, "/ergast/f1/2026/5/results.json");
  assert.equal((await call("get_competition", { competition_id: "2026/99" })).structuredContent.error, "not_found");
});
