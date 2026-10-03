import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/trading/luno.json", import.meta.url), "utf8"));
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

const m = (id, base, quote) => ({ market_id: id, trading_status: "ACTIVE", base_currency: base, counter_currency: quote, min_volume: "0.0005", max_volume: "100.00", volume_scale: 4, min_price: "10.00", max_price: "10000000.00", price_scale: 0, fee_scale: 8 });
const MARKETS = { markets: [m("SONICMYR", "SONIC", "MYR"), m("XBTZAR", "XBT", "ZAR"), m("ETHZAR", "ETH", "ZAR")] };

test("luno exposes only the public reads", async () => {
  const { client } = await connect({}, () => ({ body: {} }));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_ticker", "list_markets"]);
  assert.ok(tools.every((t) => t.annotations.readOnlyHint));
});

test("luno list_markets sorts and pages locally (wire)", async () => {
  const { client, log } = await connect({}, () => ({ body: MARKETS }));
  const p1 = (await client.callTool({ name: "list_markets", arguments: { limit: 2 } })).structuredContent;
  assert.deepEqual(p1.markets.map((x) => x.symbol), ["ETHZAR", "SONICMYR"]);
  assert.deepEqual([p1.markets[0].base, p1.markets[0].quote], ["ETH", "ZAR"]);
  assert.equal(p1.total, 3);
  assert.equal(p1.next_page, 2);
  const p2 = (await client.callTool({ name: "list_markets", arguments: { limit: 2, page: 2 } })).structuredContent;
  assert.deepEqual(p2.markets.map((x) => x.symbol), ["XBTZAR"]);
  assert.equal(p2.next_page, null);
  assert.equal(log[0].url.pathname, "/api/exchange/1/markets");
});

test("luno get_ticker maps string prices and an unknown pair is a tool error (wire)", async () => {
  const { client, log } = await connect({}, (u) => (u.searchParams.get("pair") === "XBTZAR"
    ? { body: { pair: "XBTZAR", timestamp: 1790516492037, bid: "1385193.00", ask: "1385194.00", last_trade: "1385260.00", rolling_24_hour_volume: "10.817066", status: "ACTIVE" } }
    : { status: 400, body: { error: "Market not available", error_code: "ErrMarketUnavailable" } }));
  const t = (await client.callTool({ name: "get_ticker", arguments: { symbol: "XBTZAR" } })).structuredContent;
  assert.deepEqual([t.symbol, t.last, t.bid, t.ask, t.volume], ["XBTZAR", 1385260, 1385193, 1385194, 10.817066]);
  assert.equal(log[0].url.pathname, "/api/1/ticker");
  const bad = await client.callTool({ name: "get_ticker", arguments: { symbol: "NOPEZAR" } });
  assert.equal(bad.isError, true);
  assert.equal(bad.structuredContent.error, "upstream_error");
  assert.match(bad.structuredContent.message, /ErrMarketUnavailable/);
});
