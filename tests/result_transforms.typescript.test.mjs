// Twin of tests/test_result_transforms_python.py: the same specs and the same expected outputs.
import assert from "node:assert/strict";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const BASE = "https://api.transforms.example";
const resp = (status, body) => ({ status, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null) }, text: async () => JSON.stringify(body) });
const spec = (tools, envelope) => ({ id: "transforms", category: "market_data", docs_url: "https://x", adapter: { base_url: BASE, auth: { type: "none" }, rate_per_second: 50, tools, ...(envelope ? { envelope } : {}) } });

async function connect(s, handler) {
  const fetcher = async (url) => { const r = handler(new URL(url)); return resp(r.status ?? 200, r.body); };
  const server = buildServer(s, new Transport(BASE, { type: "none" }, {}, 50, "test", fetcher, s.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("columnar rows, ragged arrays and non-array keys", async () => {
  const s = spec({ get_candles: { path: "/c", result: { items: "$", columnar: true, key: "candles", fields: { time: "str:t", open: "num:c", high: "num:c", low: "num:c", close: "num:c" } } } });
  const c = await connect(s, () => ({ body: { s: "ok", t: [1, 2, 3], c: ["1.5", "2"] } }));
  const res = (await c.callTool({ name: "get_candles", arguments: { symbol: "X", interval: "1h" } })).structuredContent;
  assert.deepEqual(res.candles.map((x) => [x.time, x.close]), [["1", 1.5], ["2", 2], ["3", null]]);
  assert.deepEqual(res.candles[0].raw, { t: 1, c: "1.5" });
});

test("slice + sort pages locally and caps the limit", async () => {
  const rows = ["D", "B", "A", "C", "E"].map((c) => ({ code: c, n: c.toLowerCase() }));
  const s = spec({ search_symbols: { path: "/all", max_limit: 2, result: { items: "$", slice: true, sort: "symbol", key: "results", fields: { symbol: "code", name: "n" } } } });
  const c = await connect(s, () => ({ body: rows }));
  const p1 = (await c.callTool({ name: "search_symbols", arguments: { query: "x", limit: 50 } })).structuredContent;
  assert.deepEqual([p1.results.map((r) => r.symbol), p1.total, p1.next_page], [["A", "B"], 5, 2]);
  const p3 = (await c.callTool({ name: "search_symbols", arguments: { query: "x", limit: 2, page: 3 } })).structuredContent;
  assert.deepEqual([p3.results.map((r) => r.symbol), p3.next_page], [["E"], null]);
  const p9 = (await c.callTool({ name: "search_symbols", arguments: { query: "x", limit: 2, page: 9 } })).structuredContent;
  assert.deepEqual([p9.results, p9.next_page], [[], null]);
});

test("fmt: and iso: result fields", async () => {
  const s = spec({ get_news: { path: "/n", result: { items: "items", key: "articles", fields: { id: "id", title: "fmt:#{id} {slug}", url: "fmt:https://site.example/p/{id}", published_at: "iso:ts", source: "iso:ms|iso" } } } });
  const c = await connect(s, () => ({ body: { items: [
    { id: 7, slug: "a-b", ts: 1438273200, ms: 1438273200123, iso: "2015-07-30T16:20:00Z" }, { id: 8, ts: "1438273200", ms: null, iso: "" }] } }));
  const a = (await c.callTool({ name: "get_news", arguments: {} })).structuredContent.articles;
  assert.deepEqual([a[0].title, a[0].url, a[0].published_at, a[0].source], ["#7 a-b", "https://site.example/p/7", "2015-07-30T16:20:00Z", "2015-07-30T16:20:00Z"]);
  assert.deepEqual([a[1].title, a[1].url, a[1].published_at, a[1].source], [null, "https://site.example/p/8", "2015-07-30T16:20:00Z", null]);
});

test("fail_when reads through arrays and uses a dotted error_field", async () => {
  const s = spec({ get_series: { path: "/d/{series_id}", result: { root: "Results.0", fields: { name: "Make" } } } }, { fail_when: { "Results.0.Make": "" }, error_field: "Results.0.ErrorText" });
  const c = await connect(s, (u) => ({ body: u.pathname.endsWith("/bad") ? { Results: [{ Make: "", ErrorText: "6 - Incomplete VIN" }] } : { Results: [{ Make: "" }] } }));
  const bad = await c.callTool({ name: "get_series", arguments: { series_id: "bad" } });
  assert.deepEqual([bad.isError, bad.structuredContent.message], [true, "6 - Incomplete VIN"]);
  const empty = await c.callTool({ name: "get_series", arguments: { series_id: "empty" } });
  assert.deepEqual([empty.isError, empty.structuredContent.message], [true, ""]);
});

test("rate limit wordings in a 200 envelope", async () => {
  for (const comment of ["Call limit exceeded", "Rate limit reached, slow down"]) {
    const s = spec({ get_news: { path: "/e", result: { items: "result", key: "articles", fields: { id: "id" } } } }, { ok_field: "status", ok_value: "OK", error_field: "comment" });
    const c = await connect(s, () => ({ body: { status: "FAILED", comment } }));
    const res = await c.callTool({ name: "get_news", arguments: {} });
    assert.deepEqual([res.isError, res.structuredContent.error], [true, "rate_limited"], comment);
  }
});

test("arg: echoes a tool argument into the result", async () => {
  const s = { id: "transforms", category: "trading", docs_url: "https://x", adapter: { base_url: BASE, auth: { type: "none" }, tools: {
    get_ticker: { path: "/ticker/{symbol}/", result: { fields: { symbol: "arg:symbol", last: "num:last", bid: "num:bid", ask: "num:ask" } } } } } };
  const c = await connect(s, () => ({ body: { last: "84810.49", bid: "84810", ask: "84811" } }));
  const r = await c.callTool({ name: "get_ticker", arguments: { symbol: "btcusd" } });
  assert.deepEqual([r.isError, r.structuredContent.symbol, r.structuredContent.last], [false, "btcusd", 84810.49]);
});
