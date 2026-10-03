import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/competitions/kaggle.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (r.status === 201 || r.status === 204 ? "" : JSON.stringify(r.body ?? {})) }; };

async function connect(handler, creds = { api_token: "KGAT_secret_value" }) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

const COMP = { id: 3136, ref: "titanic", title: "Titanic - Machine Learning from Disaster", url: "https://www.kaggle.com/competitions/titanic", category: "Getting Started", reward: "Knowledge", tags: [{ name: "tabular" }], deadline: "2030-01-01T00:00:00Z", enabledDate: "2012-09-28T21:13:33Z" };

test("kaggle: four tools (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["discover", "get_competition", "my_entries", "standings"]);
});

test("kaggle: discover POSTs search/page with a bearer token (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { competitions: [COMP], nextPageToken: "" } }; });
  const res = await client.callTool({ name: "discover", arguments: { query: "titanic", page: 2 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.competitions[0].id, "titanic");
  assert.equal(res.structuredContent.competitions[0].prize, "Knowledge");
  assert.equal(seen.url.pathname, "/v1/competitions.CompetitionApiService/ListCompetitions");
  assert.equal(seen.init.method, "POST");
  assert.deepEqual(JSON.parse(seen.init.body), { search: "titanic", page: 2 });
});

test("kaggle: standings map the leaderboard (wire)", async () => {
  const client = await connect(() => ({ body: { submissions: [{ teamId: 7, teamName: "Leaders", submissionDate: "2026-09-20T00:00:00Z", score: "0.99" }] } }));
  const res = await client.callTool({ name: "standings", arguments: { competition_id: "titanic" } });
  assert.equal(res.structuredContent.standings[0].team, "Leaders");
  assert.equal(res.structuredContent.standings[0].raw.score, "0.99");
});
