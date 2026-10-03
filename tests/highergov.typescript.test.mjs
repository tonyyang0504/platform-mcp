import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/highergov.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const dig = (o, p) => p.split(".").reduce((a, k) => (a == null ? a : a[k]), o);
process.env.PLATFORM_MCP_HIGHERGOV_API_KEY = "HG-KEY-secret123";
process.env.PLATFORM_MCP_HIGHERGOV_SEARCH_ID = "S123";

async function connect(handler) {
  const tokens = [];
  globalThis.fetch = fakeFetch((url, init) => {
    return handler(url, init);
  });
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  client.tokens = tokens;
  return client;
}

test("highergov: tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_posting", "search_postings"]);
  for (const t of tools) { assert.equal(t.inputSchema.additionalProperties, false); assert.ok(t.title); }
});

test("highergov: search_postings maps documented fields (main, wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 200, body: {"results": [{"opp_key": "OPP1", "title": "Cloud migration", "description_text": "Text", "agency": {"agency_name": "GSA"}, "posted_date": "2026-09-20", "due_date": "2026-10-20", "source_path": "https://sam.gov/opp/1"}], "meta": {"pagination": {"page": 2, "pages": 9, "count": 420}}} }; });
  const res = await client.callTool({ name: "search_postings", arguments: {"page": 2, "limit": 50} });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.deepEqual(dig(res.structuredContent, "postings.0.id"), "OPP1");
  assert.deepEqual(dig(res.structuredContent, "postings.0.buyer"), "GSA");
  assert.deepEqual(dig(res.structuredContent, "postings.0.deadline"), "2026-10-20");
  assert.deepEqual(dig(res.structuredContent, "total"), 420);
  assert.equal(seen.url.href.split("?")[0], "https://www.highergov.com/api-external/opportunity/");
  assert.equal(seen.init.method, "GET");
  assert.equal(seen.url.searchParams.get("api_key"), "HG-KEY-secret123");
  assert.equal(seen.url.searchParams.get("search_id"), "S123");
  assert.equal(seen.url.searchParams.get("page_number"), "2");
  assert.equal(seen.url.searchParams.get("page_size"), "50");
});

test("highergov: get_posting maps documented fields (extra, wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 200, body: {"results": [{"opp_key": "OPP1", "title": "Cloud migration"}], "meta": {"pagination": {"count": 1}}} }; });
  const res = await client.callTool({ name: "get_posting", arguments: {"id": "OPP1"} });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.deepEqual(dig(res.structuredContent, "id"), "OPP1");
  assert.deepEqual(dig(res.structuredContent, "title"), "Cloud migration");
  assert.equal(seen.url.href.split("?")[0], "https://www.highergov.com/api-external/opportunity/");
  assert.equal(seen.init.method, "GET");
  assert.equal(seen.url.searchParams.get("opp_key"), "OPP1");
});

test("highergov: rate limit is an isError result (wire)", async () => {
  const client = await connect(() => ({ status: 429, headers: { "Retry-After": "30" } }));
  const res = await client.callTool({ name: "search_postings", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
  assert.equal(res.structuredContent.retry_after_seconds, 30);
});
