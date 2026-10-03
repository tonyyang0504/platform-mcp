import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/infojobs.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const dig = (o, p) => p.split(".").reduce((a, k) => (a == null ? a : a[k]), o);
process.env.PLATFORM_MCP_INFOJOBS_CLIENT_ID = "ij-cid";
process.env.PLATFORM_MCP_INFOJOBS_CLIENT_SECRET = "ij-SECRETvalue";

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

test("infojobs: tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_posting", "search"]);
  for (const t of tools) { assert.equal(t.inputSchema.additionalProperties, false); assert.ok(t.title); }
});

test("infojobs: search maps documented fields (main, wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 200, body: {"currentPage": 2, "pageSize": 20, "totalResults": 35, "offers": [{"id": "abc123", "title": "Java dev", "author": {"name": "Acme SL"}, "city": "Madrid", "link": "https://www.infojobs.net/madrid/java/of-iabc123", "published": "2026-09-20T10:00:00Z"}]} }; });
  const res = await client.callTool({ name: "search", arguments: {"query": "java", "page": 2, "limit": 20} });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.deepEqual(dig(res.structuredContent, "postings.0.id"), "abc123");
  assert.deepEqual(dig(res.structuredContent, "postings.0.company"), "Acme SL");
  assert.deepEqual(dig(res.structuredContent, "postings.0.location"), "Madrid");
  assert.deepEqual(dig(res.structuredContent, "total"), 35);
  assert.equal(seen.url.href.split("?")[0], "https://api.infojobs.net/api/9/offer");
  assert.equal(seen.init.method, "GET");
  assert.equal(seen.url.searchParams.get("q"), "java");
  assert.equal(seen.url.searchParams.get("page"), "2");
  assert.equal(seen.url.searchParams.get("maxResults"), "20");
  assert.ok((seen.init.headers["Authorization"] ?? seen.init.headers["authorization"]).startsWith("Basic "));
});

test("infojobs: get_posting maps documented fields (extra, wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 200, body: {"id": "abc123", "title": "Java dev", "profile": {"name": "Acme SL"}, "city": "Madrid", "description": "Full text", "creationDate": "2026-09-01T00:00:00.000+0000"} }; });
  const res = await client.callTool({ name: "get_posting", arguments: {"id": "abc123"} });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.deepEqual(dig(res.structuredContent, "company"), "Acme SL");
  assert.deepEqual(dig(res.structuredContent, "description"), "Full text");
  assert.equal(seen.url.href.split("?")[0], "https://api.infojobs.net/api/7/offer/abc123");
  assert.equal(seen.init.method, "GET");

});

test("infojobs: rate limit is an isError result (wire)", async () => {
  const client = await connect(() => ({ status: 429, headers: { "Retry-After": "30" } }));
  const res = await client.callTool({ name: "search", arguments: {"query": "x"} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
  assert.equal(res.structuredContent.retry_after_seconds, 30);
});
