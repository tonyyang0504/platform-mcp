import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/belancer_com.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const dig = (o, p) => p.split(".").reduce((a, k) => (a == null ? a : a[k]), o);
process.env.PLATFORM_MCP_BELANCER_COM_USERNAME = "me@example.com";
process.env.PLATFORM_MCP_BELANCER_COM_PASSWORD = "PASSWORDsecret";

async function connect(handler) {
  const tokens = [];
  globalThis.fetch = fakeFetch((url, init) => {
    if (url.href.split("?")[0] === "https://belancer.com/api/auth/login") { tokens.push(init); return { body: {"access_token": "BL-TOKEN-abc", "token_type": "bearer", "user_id": 1, "role": "seller", "expires_at": "2026-09-25T00:00:00Z"} }; }
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

test("belancer_com: tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_posting", "me", "search_postings"]);
  for (const t of tools) { assert.equal(t.inputSchema.additionalProperties, false); assert.ok(t.title); }
});

test("belancer_com: search_postings maps documented fields (main, wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 200, body: {"total": 205, "page": 1, "limit": 1, "projects": [{"id": 380, "name": "Hire Broker", "description": "Need", "currency": "USD", "min_budget": 8.0, "max_budget": 30.0, "created_at": "2026-09-23T15:23:11Z"}]} }; });
  const res = await client.callTool({ name: "search_postings", arguments: {"query": "logo", "category": "553", "min_budget": 10, "page": 1, "limit": 1} });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.deepEqual(dig(res.structuredContent, "postings.0.id"), "380");
  assert.deepEqual(dig(res.structuredContent, "postings.0.budget_max"), 30.0);
  assert.deepEqual(dig(res.structuredContent, "total"), 205);
  assert.deepEqual(dig(res.structuredContent, "next_page"), 2);
  assert.equal(seen.url.href.split("?")[0], "https://belancer.com/api/projects/search");
  assert.equal(seen.init.method, "GET");
  assert.equal(seen.url.searchParams.get("query"), "logo");
  assert.equal(seen.url.searchParams.get("category_id"), "553");
  assert.equal(seen.url.searchParams.get("min_budget"), "10");
  assert.equal(seen.url.searchParams.get("page"), "1");
  assert.equal(seen.url.searchParams.get("limit"), "1");
  assert.equal(seen.url.searchParams.get("status"), "open");
  assert.equal((seen.init.headers["Authorization"] ?? seen.init.headers["authorization"]), "Bearer BL-TOKEN-abc");
  assert.deepEqual(JSON.parse(client.tokens.at(-1).body), {"username": "me@example.com", "password": "PASSWORDsecret"});
});

test("belancer_com: rate limit is an isError result (wire)", async () => {
  const client = await connect(() => ({ status: 429, headers: { "Retry-After": "30" } }));
  const res = await client.callTool({ name: "get_posting", arguments: {"id": "380"} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
  assert.equal(res.structuredContent.retry_after_seconds, 30);
});
