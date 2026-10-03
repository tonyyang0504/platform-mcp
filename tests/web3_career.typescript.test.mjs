import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/web3_career.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const dig = (o, p) => p.split(".").reduce((a, k) => (a == null ? a : a[k]), o);
process.env.PLATFORM_MCP_WEB3_CAREER_TOKEN = "W3-TOKEN-secret";

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

test("web3_career: tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["search"]);
  for (const t of tools) { assert.equal(t.inputSchema.additionalProperties, false); assert.ok(t.title); }
});

test("web3_career: search maps documented fields (main, wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 200, body: ["meta", "v1", [{"id": "123", "title": "Solidity engineer", "company": "Uniswap", "location": "Remote", "apply_url": "https://web3.career/solidity-engineer-uniswap/123?utm_source=api", "postedAt": "2026-09-20", "description": "<p>x</p>"}]] }; });
  const res = await client.callTool({ name: "search", arguments: {"query": "solidity", "limit": 5} });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.deepEqual(dig(res.structuredContent, "postings.0.id"), "123");
  assert.deepEqual(dig(res.structuredContent, "postings.0.company"), "Uniswap");
  assert.deepEqual(dig(res.structuredContent, "postings.0.url"), "https://web3.career/solidity-engineer-uniswap/123?utm_source=api");
  assert.equal(seen.url.href.split("?")[0], "https://web3.career/api/v1");
  assert.equal(seen.init.method, "GET");
  assert.equal(seen.url.searchParams.get("tag"), "solidity");
  assert.equal(seen.url.searchParams.get("limit"), "5");
  assert.equal(seen.url.searchParams.get("token"), "W3-TOKEN-secret");
});

test("web3_career: rate limit is an isError result (wire)", async () => {
  const client = await connect(() => ({ status: 429, headers: { "Retry-After": "30" } }));
  const res = await client.callTool({ name: "search", arguments: {"query": "rust"} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
  assert.equal(res.structuredContent.retry_after_seconds, 30);
});
