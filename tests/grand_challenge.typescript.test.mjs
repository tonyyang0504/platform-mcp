import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/competitions/grand_challenge.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (r.status === 201 || r.status === 204 ? "" : JSON.stringify(r.body ?? {})) }; };

async function connect(handler, creds = { api_token: "gc-token" }) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

const CH = { url: "https://vessel12.grand-challenge.org/", slug: "VESSEL12", title: "", status: "CLOSED", start_date: null, end_date: null };

test("grand_challenge: discover uses limit/offset (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { count: 264, results: [CH] } }; });
  const res = await client.callTool({ name: "discover", arguments: { page: 3, limit: 1 } });
  assert.equal(res.structuredContent.competitions[0].id, "VESSEL12");
  assert.equal(res.structuredContent.total, 264);
  assert.equal(seen.searchParams.get("offset"), "2");
});

test("grand_challenge: standings filter evaluations by phase (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { count: 1, results: [{ rank: 1, rank_score: 0.93, created: "2026-09-01T10:00:00Z", submission: { creator: { username: "alice" } } }] } }; });
  const res = await client.callTool({ name: "standings", arguments: { competition_id: "phase-uuid" } });
  assert.equal(res.structuredContent.standings[0].team, "alice");
  assert.equal(res.structuredContent.standings[0].rank, 1);
  assert.equal(seen.searchParams.get("submission__phase"), "phase-uuid");
});

test("grand_challenge: 404 is invalid_input (wire)", async () => {
  const client = await connect(() => ({ status: 404, body: { detail: "Not found." } }));
  const res = await client.callTool({ name: "get_competition", arguments: { competition_id: "nope" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "not_found");
});
