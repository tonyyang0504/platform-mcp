import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/the_muse.json", import.meta.url), "utf8"));
const JOB = { id: 12345678, name: "Senior Python Engineer", contents: "<p>You will ...</p>", publication_date: "2026-09-01T10:15:00Z", locations: [{ name: "New York, NY" }], categories: [{ name: "Software Engineering" }], levels: [{ name: "Senior Level", short_name: "senior" }], company: { id: 100, short_name: "acme", name: "Acme" }, refs: { landing_page: "https://www.themuse.com/jobs/acme/senior-python-engineer" } };
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler, creds) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("the muse search works without a key and maps documented fields (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { page: 1, page_count: 50, results: [JOB] } }; }, {});
  const res = await client.callTool({ name: "search", arguments: { query: "python", location: "New York, NY" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.postings[0].id, "12345678");
  assert.equal(res.structuredContent.postings[0].company, "Acme");
  assert.equal(res.structuredContent.postings[0].location, "New York, NY");
  assert.equal(res.structuredContent.postings[0].url, "https://www.themuse.com/jobs/acme/senior-python-engineer");
  assert.equal(seen.searchParams.get("page"), "1");
  assert.equal(seen.searchParams.get("location"), "New York, NY");
  assert.equal(seen.searchParams.get("api_key"), null);
});

test("the muse registered key travels as the api_key query parameter (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: JOB }; }, { api_key: "k" });
  const res = await client.callTool({ name: "get_posting", arguments: { id: "12345678" } });
  assert.equal(res.isError, false);
  assert.equal(seen.pathname, "/api/public/jobs/12345678");
  assert.equal(seen.searchParams.get("api_key"), "k");
});

test("the muse 403 (hourly quota) is an isError result (wire)", async () => {
  const res = await (await connect(() => ({ status: 403, body: {} }), {})).callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
});
