// Regression tests for the fixes found by platform-mcp-hub verify (live check 2026-09-26): each replays a
// response recorded from the live platform (tests/fixtures/live, personal data scrubbed) through the
// TypeScript runtime, mirroring tests/test_live_check_fixes_python.py.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";
import { paginates } from "../runtime/typescript/dist/adapter.js";

const spec = (key) => JSON.parse(readFileSync(new URL(`../catalog/${key}.json`, import.meta.url), "utf8"));
const fixture = (name) => readFileSync(new URL(`./fixtures/live/${name}`, import.meta.url), "utf8");
const json = (name) => JSON.parse(fixture(name));

async function connect(s, handler, creds = {}) {
  const log = [];
  const fetcher = async (url, init) => {
    log.push({ url: new URL(url), init });
    const r = handler(new URL(url), init);
    const type = r.type ?? "application/json";
    return { status: r.status ?? 200, headers: { get: (k) => (k.toLowerCase() === "content-type" ? type : null) }, text: async () => (typeof r.body === "string" ? r.body : JSON.stringify(r.body)) };
  };
  const server = buildServer(s, new Transport(s.adapter.base_url, s.adapter.auth, creds, 50, "test", fetcher, s.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return { client, log };
}

test("paginates() detects page, offset and cursor expressions", () => {
  assert.equal(paginates({ path: "/x", params: { page: "page" } }), true);
  assert.equal(paginates({ path: "/x", params: { os: "offset" } }), true);
  assert.equal(paginates({ path: "/x", params: { p: "page0" } }), true);
  assert.equal(paginates({ path: "/x", params: { c: "cursor" } }), true);
  assert.equal(paginates({ path: "/x", body: { from: "str:offset" } }), true);
  assert.equal(paginates({ path: "/x/{page}" }), true);
  assert.equal(paginates({ path: "/feed", params: { search: "query", limit: "limit" } }), false);
  assert.equal(paginates({ path: "/feed", params: { pagesize: "limit", x: "@page_token" } }), false);
});

test("a feed without paging answers next_page null (remote_ok, wire)", async () => {
  const rows = [{ legal: "notice" }, ...Array.from({ length: 30 }, (_, i) => ({ id: String(i), position: `Job ${i}`, company: "Acme" }))];
  const { client } = await connect(spec("jobs/remote_ok"), () => ({ body: rows }));
  const res = await client.callTool({ name: "search", arguments: { query: "developer", limit: 10 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.next_page, null);
});

test("no_brreg: size is a string; paging still advertised (recorded, wire)", async () => {
  const { client } = await connect(spec("sales/no_brreg"), () => ({ body: json("no_brreg_search.json") }));
  const res = await client.callTool({ name: "search", arguments: { query: "equinor", limit: 2 } });
  assert.equal(res.isError, false);
  const c = res.structuredContent.companies;
  assert.equal(c[0].size, "21272");
  assert.equal(c[1].size, null);
  assert.equal(res.structuredContent.next_page, 2);
});

test("world_bank_procurement: title falls back to the project name (recorded, wire)", async () => {
  const data = json("world_bank_search.json");
  const { client } = await connect(spec("deals/world_bank_procurement"), () => ({ body: data }));
  const res = await client.callTool({ name: "search_postings", arguments: { query: "consulting", limit: 3 } });
  const bare = data.procnotices.find((r) => !r.bid_description);
  const p = res.structuredContent.postings.find((x) => x.id === bare.id);
  assert.equal(p.title, bare.project_name);
  assert.ok(res.structuredContent.postings.every((x) => typeof x.title === "string"));
});

test("contracts_finder: search ids feed get_posting through Release/{id} (recorded, wire)", async () => {
  const release = json("contracts_finder_release.json");
  const rid = release.releases[0].id;
  const { client, log } = await connect(spec("deals/contracts_finder"), (url) => (url.pathname.startsWith("/Published/OCDS/Release/") ? { body: release } : { body: json("contracts_finder_search.json") }));
  const res = await client.callTool({ name: "search_postings", arguments: { limit: 2 } });
  const first = res.structuredContent.postings[0];
  assert.equal(first.id, rid);
  assert.equal(res.structuredContent.next_page, null);
  const got = await client.callTool({ name: "get_posting", arguments: { id: first.id } });
  assert.equal(got.isError, false);
  assert.equal(log[1].url.pathname, `/Published/OCDS/Release/${rid}`);
  assert.equal(got.structuredContent.id, rid);
  assert.equal(got.structuredContent.title, first.title);
});

test("nhs_jobs: asks for XML (406 to application/json) and parses the recorded feed (wire)", async () => {
  const { client, log } = await connect(spec("jobs/nhs_jobs"), (url, init) => (init.headers.Accept === "application/xml"
    ? { body: fixture("nhs_jobs_search.xml"), type: "application/xml" } : { status: 406, body: { error: "Not Acceptable" } }));
  const res = await client.callTool({ name: "search", arguments: { query: "nurse", limit: 2 } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.equal(log[0].init.headers.Accept, "application/xml");
  assert.equal(res.structuredContent.postings.length, 2);
});

test("problogger_jobs (deals): reads the live board feed (recorded, wire)", async () => {
  const { client, log } = await connect(spec("deals/problogger_jobs"), () => ({ body: fixture("problogger_wpjobboard_rss.xml"), type: "application/rss+xml" }));
  const res = await client.callTool({ name: "search_postings", arguments: { query: "writer" } });
  assert.equal(res.isError, false);
  assert.ok(res.structuredContent.postings.length >= 1);
  assert.equal(log[0].url.pathname, "/jobs/wpjobboard/xml/rss/");
  assert.deepEqual(Object.fromEntries(log[0].url.searchParams), { query: "writer", filter: "active" });
});

for (const [key, name, interval] of [["market_data/binance_collector", "binance_klines.json", "1h"], ["market_data/binance_vision_collector", "binance_klines.json", "1h"], ["market_data/bybit_collector", "bybit_kline.json", "60"]]) {
  test(`${key}: recorded candles are numbers with a string time (wire)`, async () => {
    const raw = json(name);
    const { client } = await connect(spec(key), () => ({ body: raw }));
    const res = await client.callTool({ name: "get_candles", arguments: { symbol: "BTCUSDT", interval, limit: 2 } });
    assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
    const row = Array.isArray(raw) ? raw[0] : raw.result.list[0];
    const c = res.structuredContent.candles[0];
    assert.equal(c.time, String(row[0]));
    assert.equal(c.close, Number(row[4]));
    assert.equal(typeof c.open, "number");
  });
}

for (const key of ["trading/hyperliquid", "trading/hyperliquid_spot"]) {
  test(`${key}: ticker prices are numbers (recorded, wire)`, async () => {
    const book = json("hyperliquid_l2book.json");
    const { client } = await connect(spec(key), () => ({ body: book }), { wallet_address: "0x0000000000000000000000000000000000000000" });
    const res = await client.callTool({ name: "get_ticker", arguments: { symbol: "BTC" } });
    assert.equal(res.isError, false);
    assert.equal(res.structuredContent.bid, Number(book.levels[0][0].px));
    assert.equal(res.structuredContent.ask, Number(book.levels[1][0].px));
  });
}

test("bybit_collector: an invalid symbol (200, retCode 10001) is an isError result (recorded, wire)", async () => {
  const { client } = await connect(spec("market_data/bybit_collector"), () => ({ body: json("bybit_kline_invalid_symbol.json") }));
  const res = await client.callTool({ name: "get_candles", arguments: { symbol: "ZZZNOTASYMBOL", interval: "60" } });
  assert.equal(res.isError, true);
  assert.match(res.structuredContent.message, /Symbol Is Invalid/);
});

test("polymarket_collector: series points carry a string time (recorded, wire)", async () => {
  const data = json("polymarket_prices_history.json");
  const { client } = await connect(spec("market_data/polymarket_collector"), () => ({ body: data }));
  const res = await client.callTool({ name: "get_series", arguments: { series_id: "123", start: "1790177880", end: "1790188680" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.points[0].time, String(data.data[0].timestamp));
  assert.equal(res.structuredContent.points[0].value, data.data[0].price);
});

// XML parity with the Python runtime (live check 2026-09-26: CDATA text kept its trailing space, &#038; stayed encoded)
import { xmlToObj } from "../runtime/typescript/dist/http.js";
for (const name of ["coroflot_rss", "jobwebghana_rss", "nhs_jobs_search", "problogger_wpjobboard_rss"]) {
  test(`${name}: parses to the same object as the Python runtime (recorded)`, () => {
    assert.deepEqual(xmlToObj(fixture(`${name}.xml`)), json(`${name}.parsed.json`));
  });
}

test("coroflot: a CDATA title is trimmed (recorded, wire)", async () => {
  const { client } = await connect(spec("jobs/coroflot"), () => ({ body: fixture("coroflot_rss.xml"), type: "application/rss+xml" }));
  const res = await client.callTool({ name: "search", arguments: { query: "designer" } });
  assert.equal(res.structuredContent.postings[0].title, "The Wild Collective is seeking a Graphic Designer Licensed Entertainment/Lifestyle");
});

test("eluta: the 'Too Many Requests' feed is a rate_limited error, not a posting (recorded, wire)", async () => {
  const { client } = await connect(spec("jobs/eluta"), () => ({ body: fixture("eluta_too_many_requests.xml"), type: "text/xml; charset=UTF-8" }));
  const res = await client.callTool({ name: "search", arguments: { query: "developer" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
});
