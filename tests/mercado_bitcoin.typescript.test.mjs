import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/trading/mercado_bitcoin.json", import.meta.url), "utf8"));
const resp = (status, body, type = "application/json") => ({ status, headers: { get: (k) => (k.toLowerCase() === "content-type" && body !== undefined ? type : null) }, text: async () => (body === undefined ? "" : typeof body === "string" ? body : JSON.stringify(body)) });

async function connect(creds, handler) {
  const log = [];
  const fetcher = async (url, init) => { log.push({ url: new URL(url), init }); const r = handler(new URL(url), init, log.length); return resp(r.status ?? 200, r.body, r.type); };
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...creds }, 50, "test", fetcher, a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return { client, log };
}
const hdr = (init, name) => { const h = init.headers ?? {}; const k = Object.keys(h).find((x) => x.toLowerCase() === name.toLowerCase()); return k ? h[k] : undefined; };

const SYMBOLS = { symbol: ["ETH-BRL", "BTC-BRL", "ADA-BRL"], currency: ["BRL", "BRL", "BRL"], "base-currency": ["ETH", "BTC", "ADA"], type: ["CRYPTO", "CRYPTO", "CRYPTO"] };

test("mercado_bitcoin list_markets transposes, sorts and pages locally (wire)", async () => {
  const { client, log } = await connect({}, () => ({ body: SYMBOLS }));
  const p1 = (await client.callTool({ name: "list_markets", arguments: { limit: 2 } })).structuredContent;
  assert.deepEqual(p1.markets.map((m) => m.symbol), ["ADA-BRL", "BTC-BRL"]);
  assert.equal(p1.markets[1].base, "BTC");
  assert.equal(p1.total, 3);
  assert.equal(p1.next_page, 2);
  const p2 = (await client.callTool({ name: "list_markets", arguments: { limit: 2, page: 2 } })).structuredContent;
  assert.deepEqual(p2.markets.map((m) => m.symbol), ["ETH-BRL"]);
  assert.equal(p2.next_page, null);
  assert.equal(log[0].url.pathname, "/api/v4/symbols");
});

test("mercado_bitcoin get_candles transposes UDF arrays and get_ticker reads the first row (wire)", async () => {
  const { client, log } = await connect({}, (u) => (u.pathname.endsWith("/candles")
    ? { body: { t: [1790503200, 1790506800], o: ["441283.0", "440990.0"], h: ["442065.0", "441402.0"], l: ["440751.0", "440863.0"], c: ["441159.0", "441150.0"], v: ["0.73424520", "0.13650401"] } }
    : { body: [{ pair: "BTC-BRL", last: "441600.00000000", buy: "441602.0", sell: "441603.0", vol: "5.65367181" }] }));
  const c = (await client.callTool({ name: "get_candles", arguments: { symbol: "BTC-BRL", interval: "1h", limit: 2 } })).structuredContent;
  assert.deepEqual([c.candles[0].time, c.candles[0].open, c.candles[1].close, c.candles[0].volume], ["1790503200", 441283, 441150, 0.7342452]);
  const q = log[0].url.searchParams;
  assert.deepEqual([q.get("symbol"), q.get("resolution"), q.get("countback")], ["BTC-BRL", "1h", "2"]);
  const t = (await client.callTool({ name: "get_ticker", arguments: { symbol: "BTC-BRL" } })).structuredContent;
  assert.deepEqual([t.symbol, t.last, t.bid, t.ask], ["BTC-BRL", 441600, 441602, 441603]);
});

test("mercado_bitcoin list_markets query filters symbol, base or quote; pages come from one download (wire)", async () => {
  const { client, log } = await connect({}, () => ({ body: SYMBOLS }));
  const r = (await client.callTool({ name: "list_markets", arguments: { query: "btc" } })).structuredContent;
  assert.deepEqual([r.markets.map((m) => m.symbol), r.total], [["BTC-BRL"], 1]);
  const p2 = (await client.callTool({ name: "list_markets", arguments: { query: "brl", limit: 2, page: 2 } })).structuredContent;
  assert.deepEqual([p2.markets.map((m) => m.symbol), p2.total, log.length], [["ETH-BRL"], 3, 1]);
});
