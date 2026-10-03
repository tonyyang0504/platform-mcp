import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/hn_who_is_hiring.json", import.meta.url), "utf8"));
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

test("hn_who_is_hiring: tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_posting"]);
  for (const t of tools) { assert.equal(t.inputSchema.additionalProperties, false); assert.ok(t.title); }
});

test("hn_who_is_hiring: get_posting maps documented fields (main, wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 200, body: {"id": 45000001, "by": "acme_hiring", "text": "Acme | Backend engineer | Remote", "time": 1758700000, "type": "comment", "parent": 45000000} }; });
  const res = await client.callTool({ name: "get_posting", arguments: {"id": "45000001"} });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.deepEqual(dig(res.structuredContent, "id"), "45000001");
  assert.deepEqual(dig(res.structuredContent, "company"), "acme_hiring");
  assert.deepEqual(dig(res.structuredContent, "title"), "Acme | Backend engineer | Remote");
  assert.equal(seen.url.href.split("?")[0], "https://hacker-news.firebaseio.com/v0/item/45000001.json");
  assert.equal(seen.init.method, "GET");

});

test("hn_who_is_hiring: rate limit is an isError result (wire)", async () => {
  const client = await connect(() => ({ status: 429, headers: { "Retry-After": "30" } }));
  const res = await client.callTool({ name: "get_posting", arguments: {"id": "1"} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
  assert.equal(res.structuredContent.retry_after_seconds, 30);
});
