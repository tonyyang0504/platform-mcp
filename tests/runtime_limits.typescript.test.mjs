// Twin of tests/test_runtime_limits_python.py: the error-kind table and adapter.error_kinds, the bounded
// response cache for locally paged collections, result.filter on sliced feeds and page-only mapping.
import assert from "node:assert/strict";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, classify, ResponseCache, Transport } from "../runtime/typescript/dist/index.js";

const BASE = "https://api.limits.example";
const SECRET = "sk-live-0123456789abcdef";
const AUTH = { type: "bearer", field: "token", fields: [{ name: "token" }] };
const resp = (status, body, headers = {}) => ({
  status,
  headers: { get: (k) => (k.toLowerCase() === "content-type" ? (typeof body === "string" ? "text/plain" : "application/json") : headers[k] ?? headers[k.toLowerCase()] ?? null) },
  text: async () => (typeof body === "string" ? body : JSON.stringify(body)),
});
const spec = (tools, category = "market_data", extra = {}) => ({ id: "limits", category, docs_url: "https://x", adapter: { base_url: BASE, auth: AUTH, rate_per_second: 50, tools, ...extra } });

async function connect(s, handler, cache) {
  const log = [];
  const fetcher = async (url, init) => { log.push({ url: new URL(url), init }); const r = handler(new URL(url), log.length); return resp(r.status ?? 200, r.body, r.headers); };
  const t = new Transport(BASE, AUTH, { token: SECRET }, 50, "test", fetcher, s.adapter.envelope ?? {});
  if (cache) t.cache = cache;
  const server = buildServer(s, t);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return { client, log, t };
}

const SERIES = { get_series: { path: "/s/{series_id}", result: { root: "data", fields: { name: "n" } } } };
const SEARCH = { search_symbols: { path: "/q", params: { q: "query" }, result: { items: "data", key: "results", fields: { symbol: "s" } } } };

const TABLE = [
  [400, { message: "Invalid parameter 'from': must be a date" }, "GET", "invalid_input"],
  [422, { status: 422, message: "invalid currency: XXXQ" }, "GET", "invalid_input"],
  [422, "Failed to deserialize the JSON body", "POST", "invalid_input"],
  [400, { status: "FAILED", comment: "contestId: Contest with id 99999999 not found" }, "GET", "not_found"],
  [400, { error: "API key not valid. Please pass a valid API key." }, "GET", "auth_error"],
  [400, { status: "FAILED", comment: "Call limit exceeded" }, "GET", "rate_limited"],
  [400, { oops: 1 }, "GET", "upstream_error"],
  [401, { error: "unauthorized" }, "GET", "auth_error"],
  [403, "forbidden", "GET", "auth_error"],
  [404, { error: "no such series" }, "GET", "not_found"],
  [404, { error: "no such order" }, "POST", "invalid_input"],
  [409, { error: "version mismatch" }, "PUT", "conflict"],
  [410, "gone", "GET", "not_found"],
  [429, "slow down", "GET", "rate_limited"],
  [500, { error: "invalid state" }, "GET", "upstream_error"],
  [502, "bad gateway", "GET", "upstream_error"],
  [503, "", "GET", "upstream_error"],
];

test("classify table (same rows as the Python twin)", () => {
  for (const [status, body, method, kind] of TABLE) {
    const Kind = classify(status, typeof body === "string" ? body : JSON.stringify(body), { method });
    assert.equal(new Kind("x").kind, kind, `${status} ${JSON.stringify(body)} ${method}`);
  }
});

test("HTTP errors through a tool carry the kind, the status and no secret", async () => {
  const bodies = { a: [400, { message: `invalid series key; token ${SECRET} ok` }], b: [404, { error: "unknown" }], c: [409, { error: "busy" }], d: [503, "maintenance"], e: [429, "x", { "Retry-After": "7" }] };
  const { client } = await connect(spec(SERIES), (u) => { const [status, body, headers] = bodies[u.pathname.split("/").pop()]; return { status, body, headers }; });
  const got = {};
  for (const k of "abcde") { const r = await client.callTool({ name: "get_series", arguments: { series_id: k } }); assert.equal(r.isError, true); got[k] = r.structuredContent; }
  assert.deepEqual([got.a.error, got.a.http_status], ["invalid_input", 400]);
  assert.ok(!got.a.message.includes(SECRET) && got.a.message.includes("invalid series key"));
  assert.deepEqual([got.b.error, got.c.error, got.d.error], ["not_found", "conflict", "upstream_error"]);
  assert.deepEqual([got.e.error, got.e.retry_after_seconds], ["rate_limited", 7]);
});

test("error_kinds overrides win for HTTP statuses and envelopes", async () => {
  const rules = [{ status: 500, match: "unknown symbol", kind: "invalid_input" }, { status: 400, kind: "upstream_error" }, { status: 200, match: "no data", kind: "not_found" }];
  const bodies = { a: [500, { msg: "Unknown symbol ZZZ" }], b: [400, { msg: "invalid parameter" }], c: [200, { ok: false, msg: "No data for this key" }], d: [500, { msg: "db down" }] };
  const { client } = await connect(spec(SERIES, "market_data", { error_kinds: rules, envelope: { ok_field: "ok", error_field: "msg" } }), (u) => { const [status, body] = bodies[u.pathname.split("/").pop()]; return { status, body }; });
  const kinds = [];
  for (const k of "abcd") kinds.push((await client.callTool({ name: "get_series", arguments: { series_id: k } })).structuredContent.error);
  assert.deepEqual(kinds, ["invalid_input", "upstream_error", "not_found", "upstream_error"]);
});

test("an empty record on a GET is not_found", async () => {
  const { client } = await connect(spec(SERIES), () => ({ body: { data: {} } }));
  const r = await client.callTool({ name: "get_series", arguments: { series_id: "x" } });
  assert.deepEqual([r.structuredContent.error, r.structuredContent.http_status], ["not_found", 404]);
});

const SLICED = { search_symbols: { path: "/all", max_limit: 100, result: { items: "$", slice: true, key: "results", fields: { symbol: "s", name: "n" } } } };
const ROWS = Array.from({ length: 10 }, (_, i) => ({ s: `S${String(i).padStart(2, "0")}`, n: `name ${i}` }));

test("paging a sliced collection downloads it once within the TTL", async () => {
  const { client, log, t } = await connect(spec(SLICED), () => ({ body: ROWS }));
  const pages = [];
  for (const page of [1, 2, 3]) pages.push((await client.callTool({ name: "search_symbols", arguments: { query: "x", limit: 4, page } })).structuredContent);
  assert.deepEqual(pages.map((p) => p.results.map((r) => r.symbol)), [["S00", "S01", "S02", "S03"], ["S04", "S05", "S06", "S07"], ["S08", "S09"]]);
  assert.deepEqual([pages.map((p) => p.next_page), pages[0].total], [[2, 3, null], 10]);
  assert.deepEqual([log.length, t.cache.hits], [1, 2]);
});

test("cache entries expire after the TTL", async () => {
  const { client, log } = await connect(spec({ search_symbols: { ...SLICED.search_symbols, cache_ttl: 0.05 } }), () => ({ body: ROWS }));
  await client.callTool({ name: "search_symbols", arguments: { query: "x" } });
  await new Promise((r) => setTimeout(r, 120));
  await client.callTool({ name: "search_symbols", arguments: { query: "x" } });
  assert.equal(log.length, 2);
});

test("the cache is bounded by bytes and entries and skips oversized bodies", async () => {
  const body = Buffer.byteLength(JSON.stringify(ROWS));
  const tools = { search_symbols: { ...SLICED.search_symbols, params: { q: "query" } } };
  const a = await connect(spec(tools), () => ({ body: ROWS }), new ResponseCache(body * 2, 8));
  for (const q of ["a", "b", "c"]) await a.client.callTool({ name: "search_symbols", arguments: { query: q } });
  assert.ok(a.t.cache.bytes <= body * 2 && a.t.cache.hits === 0);
  await a.client.callTool({ name: "search_symbols", arguments: { query: "a" } }); // evicted (least recently used): fetched again
  assert.equal(a.log.length, 4);
  const b = await connect(spec(tools), () => ({ body: ROWS }), new ResponseCache(body - 1, 8));
  await b.client.callTool({ name: "search_symbols", arguments: { query: "a" } });
  await b.client.callTool({ name: "search_symbols", arguments: { query: "a" } });
  assert.deepEqual([b.t.cache.bytes, b.log.length], [0, 2]); // larger than the cap: never stored
  const c = await connect(spec(tools), () => ({ body: ROWS }), new ResponseCache(10_000_000, 1));
  await c.client.callTool({ name: "search_symbols", arguments: { query: "a" } });
  await c.client.callTool({ name: "search_symbols", arguments: { query: "b" } });
  await c.client.callTool({ name: "search_symbols", arguments: { query: "b" } });
  assert.deepEqual([c.log.length, c.t.cache.bytes], [2, body]); // one entry: the latest
});

test("the cache can be disabled and never holds failures or uncached tools", async () => {
  const seq = [{ body: { ok: false, msg: "call limit exceeded" } }, { body: ROWS }, { body: ROWS }];
  const a = await connect(spec(SLICED, "market_data", { envelope: { ok_field: "ok", error_field: "msg" } }), (_u, n) => seq[n - 1]);
  const r = await a.client.callTool({ name: "search_symbols", arguments: { query: "x" } });
  assert.equal(r.structuredContent.error, "rate_limited"); // a 200 envelope failure: not cached
  await a.client.callTool({ name: "search_symbols", arguments: { query: "x" } });
  await a.client.callTool({ name: "search_symbols", arguments: { query: "x", page: 2 } });
  assert.equal(a.log.length, 2);
  const b = await connect(spec(SEARCH), () => ({ body: { data: [{ s: "A" }] } }));
  await b.client.callTool({ name: "search_symbols", arguments: { query: "a" } });
  await b.client.callTool({ name: "search_symbols", arguments: { query: "a" } });
  assert.equal(b.log.length, 2); // a server-paged tool is never cached
  process.env.PLATFORM_MCP_CACHE_MAX_MB = "0";
  assert.equal(new ResponseCache().enabled, false);
  delete process.env.PLATFORM_MCP_CACHE_MAX_MB;
  process.env.PLATFORM_MCP_CACHE_TTL = "0";
  try {
    const c = await connect(spec(SLICED), () => ({ body: ROWS }));
    await c.client.callTool({ name: "search_symbols", arguments: { query: "x" } });
    await c.client.callTool({ name: "search_symbols", arguments: { query: "x" } });
    assert.equal(c.log.length, 2); // TTL 0: caching off for sliced tools
  } finally { delete process.env.PLATFORM_MCP_CACHE_TTL; }
});

const FILTERED = { discover: { path: "/c", max_limit: 100, result: { items: "result", slice: true, key: "competitions",
  filter: [{ arg: "query", fields: ["title"] }, { arg: "kind", fields: ["kind"], match: "equals" },
    { arg: "status", fields: ["status"], match: "equals", value: "map:status:open=CODING,upcoming=BEFORE,completed=FINISHED" }],
  fields: { id: "id", title: "name", kind: "=coding", status: "phase" } } } };
const CONTESTS = { result: [{ id: 1, name: "Round 1 (Div. 2)", phase: "FINISHED" }, { id: 2, name: "Educational Round", phase: "BEFORE" },
  { id: 3, name: "Round 3 (Div. 1)", phase: "CODING" }, { id: 4, name: "Global Round", phase: "FINISHED" }] };

test("filters apply to sliced feeds before paging", async () => {
  const { client } = await connect(spec(FILTERED, "competitions"), () => ({ body: CONTESTS }));
  const ids = async (args) => { const r = (await client.callTool({ name: "discover", arguments: args })).structuredContent; return [r.competitions.map((c) => c.id), r.total, r.next_page]; };
  assert.deepEqual(await ids({ query: "round" }), [["1", "2", "3", "4"], 4, null]);
  assert.deepEqual(await ids({ query: "DIV." }), [["1", "3"], 2, null]);
  assert.deepEqual(await ids({ status: "completed" }), [["1", "4"], 2, null]);
  assert.deepEqual(await ids({ status: "upcoming", query: "round" }), [["2"], 1, null]);
  assert.deepEqual(await ids({ kind: "design" }), [[], 0, null]);
  assert.deepEqual(await ids({ query: "round", limit: 3, page: 1 }), [["1", "2", "3"], 4, 2]);
  const bad = await client.callTool({ name: "discover", arguments: { status: "someday" } });
  assert.deepEqual([bad.isError, bad.structuredContent.error], [true, "invalid_input"]);
});

test("page-only mapping gives the same page as mapping everything", async () => {
  const { client } = await connect(spec(SLICED), () => ({ body: [...ROWS, "not a record", 7] }));
  const r = (await client.callTool({ name: "search_symbols", arguments: { query: "x", limit: 3, page: 4 } })).structuredContent;
  assert.deepEqual([r.results.map((x) => x.symbol), r.total, r.next_page], [["S09"], 10, null]);
  assert.deepEqual(r.results[0].raw, { s: "S09", n: "name 9" });
});
