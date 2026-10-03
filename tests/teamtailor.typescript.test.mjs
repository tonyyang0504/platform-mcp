import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/teamtailor.json", import.meta.url), "utf8"));
const KEY = "tt_public_key_abc123xyz";
const JOB = { id: "1", attributes: { title: "Backend Developer", body: "<p>Ship it</p>", "min-salary": 40000, currency: "SEK" }, links: { "careersite-job-url": "https://career.example.com/jobs/1" } };
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler, host = "api.teamtailor.com") {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_key: KEY, api_host: host }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("search sends Token header, version header, filters and paging (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { data: [JOB], meta: { "record-count": 41 } } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "backend", page: 2, limit: 50 } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.origin + seen.url.pathname, "https://api.teamtailor.com/v1/jobs");
  assert.equal(seen.init.headers.Authorization, `Token token=${KEY}`);
  assert.equal(seen.init.headers["X-Api-Version"], "20240904");
  assert.equal(seen.url.searchParams.get("filter[status]"), "published");
  assert.equal(seen.url.searchParams.get("page[number]"), "2");
  assert.equal(seen.url.searchParams.get("page[size]"), "30");
  assert.equal(res.structuredContent.total, 41);
  assert.equal(res.structuredContent.postings[0].title, "Backend Developer");
});

test("NA stack get_posting (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { data: JOB } }; }, "api.na.teamtailor.com");
  const res = await client.callTool({ name: "get_posting", arguments: { id: "1" } });
  assert.equal(res.isError, false);
  assert.equal(seen.origin + seen.pathname, "https://api.na.teamtailor.com/v1/jobs/1");
  assert.equal(res.structuredContent.salary_min, 40000);
});

test("401 is auth_error and the key is scrubbed (wire)", async () => {
  const client = await connect(() => ({ status: 401, body: { errors: [{ title: `Invalid token ${KEY}` }] } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.ok(!JSON.stringify(res).includes(KEY));
});
