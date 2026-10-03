import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/saramin.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const dig = (o, p) => p.split(".").reduce((a, k) => (a == null ? a : a[k]), o);
process.env.PLATFORM_MCP_SARAMIN_ACCESS_KEY = "SR-KEY-secret123";

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

test("saramin: tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["search"]);
  for (const t of tools) { assert.equal(t.inputSchema.additionalProperties, false); assert.ok(t.title); }
});

test("saramin: search maps documented fields (main, wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 200, body: {"jobs": {"count": 1, "start": 1, "total": "7629", "job": [{"url": "http://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=27614114", "active": 1, "company": {"detail": {"href": "http://x", "name": "(주)사람인"}}, "position": {"title": "사무보조", "location": {"code": "101050", "name": "서울 > 관악구"}}, "id": "27614114", "posting-date": "2019-05-30T13:46:04+0900"}]}} }; });
  const res = await client.callTool({ name: "search", arguments: {"query": "웹 퍼블리셔", "page": 2, "limit": 20} });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.deepEqual(dig(res.structuredContent, "postings.0.id"), "27614114");
  assert.deepEqual(dig(res.structuredContent, "postings.0.company"), "(주)사람인");
  assert.deepEqual(dig(res.structuredContent, "postings.0.location"), "서울 > 관악구");
  assert.deepEqual(dig(res.structuredContent, "postings.0.posted_at"), "2019-05-30T13:46:04+0900");
  assert.deepEqual(dig(res.structuredContent, "total"), null);
  assert.equal(seen.url.href.split("?")[0], "https://oapi.saramin.co.kr/job-search");
  assert.equal(seen.init.method, "GET");
  assert.equal(seen.url.searchParams.get("keywords"), "웹 퍼블리셔");
  assert.equal(seen.url.searchParams.get("start"), "1");
  assert.equal(seen.url.searchParams.get("count"), "20");
  assert.equal(seen.url.searchParams.get("fields"), "posting-date");
  assert.equal(seen.url.searchParams.get("access-key"), "SR-KEY-secret123");
});

test("saramin: rate limit is an isError result (wire)", async () => {
  const client = await connect(() => ({ status: 429, headers: { "Retry-After": "30" } }));
  const res = await client.callTool({ name: "search", arguments: {"query": "x"} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
  assert.equal(res.structuredContent.retry_after_seconds, 30);
});
