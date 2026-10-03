import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/reed.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_key: "k" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("tools follow the vocabulary and carry annotations (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_posting", "me", "search"]);
  const search = tools.find((t) => t.name === "search");
  assert.equal(search.annotations.readOnlyHint, true);
  assert.equal(search.annotations.destructiveHint, false);
  assert.equal(search.title, "Search job postings");
  assert.deepEqual(search.inputSchema.required, ["query"]);
  assert.equal(search.inputSchema.additionalProperties, false);
  assert.equal(search.outputSchema.properties.postings.type, "array");
  assert.equal(search._meta["platform_mcp/endpoint"], "/search");
});

test("search maps documented fields and pagination (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { results: [{ jobId: 1, jobTitle: "Python dev", employerName: "Acme", locationName: "London", jobUrl: "https://www.reed.co.uk/jobs/1", date: "01/09/2026", minimumSalary: 50000, maximumSalary: 60000, currency: "GBP", jobDescription: "..." }], totalResults: 1 } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "python", location: "London" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.postings[0].id, "1");
  assert.equal(res.structuredContent.postings[0].company, "Acme");
  assert.equal(res.structuredContent.total, 1);
  assert.equal(res.structuredContent.next_page, null);
  assert.equal(seen.url.searchParams.get("keywords"), "python");
  assert.equal(seen.url.searchParams.get("resultsToTake"), "25");
  assert.equal(seen.url.searchParams.get("resultsToSkip"), "0");
  assert.ok(seen.init.headers.Authorization.startsWith("Basic "));
});

test("rate limit is an isError result, not a protocol error (wire)", async () => {
  const client = await connect(() => ({ status: 429, headers: { "Retry-After": "30" } }));
  const res = await client.callTool({ name: "get_posting", arguments: { id: "9" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
  assert.equal(res.structuredContent.retry_after_seconds, 30);
});
