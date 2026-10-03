import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/fourdayweek.json", import.meta.url), "utf8"));
const JOB = { id: "01a0d375-6596-792f-b378-c7980684ede8", slug: "cloud-engineer-tech-lead-at-luscii-62e771ef", title: "Cloud Engineer (Tech Lead)", description: "At Luscii ...", url: "https://4dayweek.io/job/cloud-engineer-tech-lead-at-luscii-62e771ef", work_arrangement: "remote", locations: [{ city: "Utrecht", country: "Netherlands", is_primary: true }], salary_min: 678200, salary_max: 722200, salary_currency: "EUR", salary_period: "month", posted_at: "2026-09-24T12:48:01Z", company: { slug: "luscii", name: "Luscii" } };
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, {}, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("tools follow the vocabulary and carry annotations (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_posting", "search"]);
  const search = tools.find((t) => t.name === "search");
  assert.equal(search.annotations.readOnlyHint, true);
  assert.deepEqual(search.inputSchema.required, ["query"]);
  assert.equal(search._meta["platform_mcp/endpoint"], "/api/v2/jobs");
  assert.equal(search._meta["platform_mcp/docs"], "https://4dayweek.io/developers");
});

test("search maps q, country, page, limit and the cent salaries (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { data: [JOB], page: 1, limit: 1, total: 15150, has_more: true } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "engineer", location: "Netherlands", limit: 1 } });
  assert.equal(res.isError, false);
  const p = res.structuredContent.postings[0];
  assert.equal(p.id, "cloud-engineer-tech-lead-at-luscii-62e771ef");
  assert.equal(p.company, "Luscii");
  assert.equal(p.location, "Netherlands");
  assert.equal(p.salary_min, 678200);
  assert.equal(p.currency, "EUR");
  assert.equal(res.structuredContent.total, 15150);
  assert.equal(res.structuredContent.next_page, 2);
  assert.equal(seen.url.searchParams.get("q"), "engineer");
  assert.equal(seen.url.searchParams.get("country"), "Netherlands");
  assert.equal(seen.url.searchParams.get("page"), "1");
  assert.equal(seen.url.searchParams.get("limit"), "1");
  assert.equal(seen.init.headers.Authorization, undefined);
});

test("get_posting reads the slug endpoint (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: JOB }; });
  const res = await client.callTool({ name: "get_posting", arguments: { id: "cloud-engineer-tech-lead-at-luscii-62e771ef" } });
  assert.equal(res.isError, false);
  assert.equal(seen.pathname, "/api/v2/jobs/cloud-engineer-tech-lead-at-luscii-62e771ef");
  assert.equal(res.structuredContent.title, "Cloud Engineer (Tech Lead)");
  assert.equal(res.structuredContent.description, "At Luscii ...");
});

test("rate limit is an isError result with Retry-After (wire)", async () => {
  const client = await connect(() => ({ status: 429, headers: { "Retry-After": "12" } }));
  const res = await client.callTool({ name: "search", arguments: { query: "python" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
  assert.equal(res.structuredContent.retry_after_seconds, 12);
});
