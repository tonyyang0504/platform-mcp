import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/competitions/evalai.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (r.status === 201 || r.status === 204 ? "" : JSON.stringify(r.body ?? {})) }; };

async function connect(handler, creds = { auth_token: "ev-token", participant_team_id: "42337" }) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

const CHALLENGE = { id: 2717, title: "Dr.DocBench Challenge", start_date: "2026-08-10T00:00:00Z", end_date: "2026-10-10T12:59:59Z", domain_name: null, list_tags: ["emnlp-2026"] };

test("evalai: discover lists present challenges (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { count: 1, next: null, results: [CHALLENGE] } }; });
  const res = await client.callTool({ name: "discover", arguments: {} });
  assert.equal(res.structuredContent.competitions[0].id, "2717");
  assert.equal(res.structuredContent.total, 1);
  assert.equal(seen.pathname, "/api/challenges/challenge/present/approved/public");
});

test("evalai: standings read the phase-split leaderboard (wire)", async () => {
  const client = await connect(() => ({ body: { count: 23, results: [{ submission__participant_team__team_name: "PSK", filtering_score: 75.91, submission__submitted_at: "2026-09-20T16:33:05Z" }] } }));
  const res = await client.callTool({ name: "standings", arguments: { competition_id: "7035" } });
  assert.equal(res.structuredContent.standings[0].team, "PSK");
  assert.equal(res.structuredContent.standings[0].score, 75.91);
});

test("evalai: enter posts the configured team (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 201 }; });
  const res = await client.callTool({ name: "enter", arguments: { competition_id: "2717" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "registered");
  assert.equal(seen.init.method, "POST");
  assert.equal(seen.url.pathname, "/api/challenges/challenge/2717/participant_team/42337");
});
