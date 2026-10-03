import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/landing_jobs.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const JOB = { id: 19513, title: "SQL Bridge Engineer", currency_code: "EUR", gross_salary_low: 80000, gross_salary_high: 95000, role_description: "<div>x</div>",
  published_at: "2026-01-26T14:51:00.487Z", url: "https://landing.jobs/at/oralpro-llc/sql-bridge-engineer", locations: [{ city: "Lisbon", country_code: "PT" }] };

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("landing_jobs: keyless tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_posting", "search"]);
  for (const t of tools) { assert.equal(t.inputSchema.additionalProperties, false); assert.ok(t.title); }
});

test("landing_jobs: search sends offset/limit and maps fields (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: [JOB] }; });
  const res = await client.callTool({ name: "search", arguments: { query: "sql", page: 3, limit: 10 } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  const p = res.structuredContent.postings[0];
  assert.equal(p.id, "19513"); assert.equal(p.location, "Lisbon"); assert.equal(p.salary_max, 95000); assert.equal(p.currency, "EUR");
  assert.equal(seen.url.href.split("?")[0], "https://landing.jobs/api/v1/jobs");
  assert.equal(seen.url.searchParams.get("offset"), "20");
  assert.equal(seen.url.searchParams.get("limit"), "10");
  assert.equal(seen.url.searchParams.get("query"), null);
});

test("landing_jobs: get_posting reads one job (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: JOB }; });
  const res = await client.callTool({ name: "get_posting", arguments: { id: "19513" } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.equal(res.structuredContent.title, "SQL Bridge Engineer");
  assert.equal(seen.pathname, "/api/v1/jobs/19513");
});

test("landing_jobs: rate limit is an isError result (wire)", async () => {
  const client = await connect(() => ({ status: 429, headers: { "Retry-After": "30" } }));
  const res = await client.callTool({ name: "search", arguments: { query: "x" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
});
