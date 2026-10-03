import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/freelancer_com.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const dig = (o, p) => p.split(".").reduce((a, k) => (a == null ? a : a[k]), o);
process.env.PLATFORM_MCP_FREELANCER_COM_ACCESS_TOKEN = "FL-TOKEN-secret";

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

test("freelancer_com: tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_posting", "list_messages", "search"]);
  for (const t of tools) { assert.equal(t.inputSchema.additionalProperties, false); assert.ok(t.title); }
});

test("freelancer_com: search maps documented fields (main, wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 200, body: {"status": "success", "result": {"total_count": 57, "projects": [{"id": 101, "title": "Build a scraper", "description": "Full", "budget": {"minimum": 30, "maximum": 250}, "currency": {"code": "USD"}, "time_submitted": 1758700000}]}} }; });
  const res = await client.callTool({ name: "search", arguments: {"query": "python scraper", "page": 3, "limit": 10} });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.deepEqual(dig(res.structuredContent, "postings.0.id"), "101");
  assert.deepEqual(dig(res.structuredContent, "postings.0.salary_max"), 250);
  assert.deepEqual(dig(res.structuredContent, "postings.0.currency"), "USD");
  assert.deepEqual(dig(res.structuredContent, "total"), 57);
  assert.equal(seen.url.href.split("?")[0], "https://www.freelancer.com/api/projects/0.1/projects/active/");
  assert.equal(seen.init.method, "GET");
  assert.equal(seen.url.searchParams.get("query"), "python scraper");
  assert.equal(seen.url.searchParams.get("limit"), "10");
  assert.equal(seen.url.searchParams.get("offset"), "20");
  assert.equal(seen.url.searchParams.get("full_description"), "true");
  assert.equal((seen.init.headers["freelancer-oauth-v1"] ?? seen.init.headers["freelancer-oauth-v1"]), "FL-TOKEN-secret");
});

test("freelancer_com: list_messages maps documented fields (extra, wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 200, body: {"status": "success", "result": {"messages": [{"id": 5, "thread_id": 77, "from_user": 9, "message": "hi", "time_created": 1758700000}]}} }; });
  const res = await client.callTool({ name: "list_messages", arguments: {"thread_id": "77"} });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.deepEqual(dig(res.structuredContent, "messages.0.id"), "5");
  assert.deepEqual(dig(res.structuredContent, "messages.0.thread_id"), "77");
  assert.deepEqual(dig(res.structuredContent, "messages.0.text"), "hi");
  assert.equal(seen.url.href.split("?")[0], "https://www.freelancer.com/api/messages/0.1/messages/");
  assert.equal(seen.init.method, "GET");
  assert.equal(seen.url.searchParams.get("threads[]"), "77");
});

test("freelancer_com: rate limit is an isError result (wire)", async () => {
  const client = await connect(() => ({ status: 429, headers: { "Retry-After": "30" } }));
  const res = await client.callTool({ name: "get_posting", arguments: {"id": "101"} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
  assert.equal(res.structuredContent.retry_after_seconds, 30);
});
