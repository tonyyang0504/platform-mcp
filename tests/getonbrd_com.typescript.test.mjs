import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/getonbrd_com.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const dig = (o, p) => p.split(".").reduce((a, k) => (a == null ? a : a[k]), o);


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

test("getonbrd_com: tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["search_postings"]);
  for (const t of tools) { assert.equal(t.inputSchema.additionalProperties, false); assert.ok(t.title); }
});

test("getonbrd_com: search_postings maps documented fields (main, wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 200, body: {"data": [{"id": "react-dev-acme", "attributes": {"title": "React dev", "company": {"data": {"attributes": {"name": "Acme"}}}, "min_salary": 2000, "max_salary": 3000, "description": "x"}, "links": {"public_url": "https://www.getonbrd.com/jobs/react-dev-acme"}}]} }; });
  const res = await client.callTool({ name: "search_postings", arguments: {"query": "react", "page": 2, "limit": 10} });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.deepEqual(dig(res.structuredContent, "postings.0.id"), "react-dev-acme");
  assert.deepEqual(dig(res.structuredContent, "postings.0.buyer"), "Acme");
  assert.deepEqual(dig(res.structuredContent, "postings.0.budget_max"), 3000);
  assert.equal(seen.url.href.split("?")[0], "https://www.getonbrd.com/api/v0/search/jobs");
  assert.equal(seen.init.method, "GET");
  assert.equal(seen.url.searchParams.get("query"), "react");
  assert.equal(seen.url.searchParams.get("page"), "2");
  assert.equal(seen.url.searchParams.get("per_page"), "10");
  assert.equal(seen.url.searchParams.has("remote"), false);
});

test("getonbrd_com: rate limit is an isError result (wire)", async () => {
  const client = await connect(() => ({ status: 429, headers: { "Retry-After": "30" } }));
  const res = await client.callTool({ name: "search_postings", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
  assert.equal(res.structuredContent.retry_after_seconds, 30);
});
