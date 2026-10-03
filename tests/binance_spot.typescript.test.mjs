import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/trading/binance_spot.json", import.meta.url), "utf8"));
const resp = (status, body) => ({ status, headers: { get: (k) => (k.toLowerCase() === "content-type" && body !== undefined ? "application/json" : null) }, text: async () => (body === undefined ? "" : JSON.stringify(body)) });

async function connect(creds, handler) {
  const log = [];
  const fetcher = async (url, init) => { log.push({ url: new URL(url), init }); const r = handler(new URL(url), init, log.length); return resp(r.status ?? 200, r.body); };
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...creds }, 50, "test", fetcher, a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return { client, log };
}
const hmacHex = (secret, payload) => crypto.createHmac("sha256", secret).update(payload).digest("hex");
const CREDS = { api_key: "KEY-binance-abcdef", api_secret: "SECRET-binance-abcdef" };
const signedParams = (entry) => {
  const q = entry.url.href.split("?")[1]; const cut = q.lastIndexOf("&signature=");
  const signed = q.slice(0, cut);
  assert.equal(q.slice(cut + 11), hmacHex(CREDS.api_secret, signed));
  assert.equal(entry.init.headers["X-MBX-APIKEY"], CREDS.api_key);
  assert.ok(!entry.url.href.includes(CREDS.api_secret));
  return Object.fromEntries(signed.split("&").map((p) => p.split("=")));
};

test("binance_spot offers the signed account and trading verbs (wire)", async () => {
  const { client } = await connect(CREDS, () => ({ body: {} }));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["cancel_order", "get_balances", "get_candles", "get_ticker", "list_markets", "list_orders", "me", "place_order"]);
  const po = tools.find((t) => t.name === "place_order");
  assert.equal(po.annotations.destructiveHint, true);
  assert.ok(po.description.includes("REAL ORDER WITH REAL FUNDS"));
});

test("binance_spot get_balances is HMAC-signed over the query (wire)", async () => {
  const { client, log } = await connect(CREDS, () => ({ body: { canTrade: true, balances: [{ asset: "BTC", free: "0.5", locked: "0.1" }] } }));
  const res = await client.callTool({ name: "get_balances", arguments: {} });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.balances[0].asset, "BTC");
  assert.equal(signedParams(log[0]).omitZeroBalances, "true");
});

test("binance_spot place_order limit and market (wire)", async () => {
  const { client, log } = await connect(CREDS, () => ({ body: { symbol: "BTCUSDT", orderId: 28, clientOrderId: "x", status: "NEW", origQty: "0.01", executedQty: "0" } }));
  const res = await client.callTool({ name: "place_order", arguments: { symbol: "BTCUSDT", side: "buy", type: "limit", quantity: 0.01, price: 65000.5 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.order_id, "28");
  assert.equal(log[0].init.method, "POST");
  const p = signedParams(log[0]);
  assert.deepEqual([p.symbol, p.side, p.type, p.timeInForce, p.quantity, p.price], ["BTCUSDT", "BUY", "LIMIT", "GTC", "0.01", "65000.5"]);
  await client.callTool({ name: "place_order", arguments: { symbol: "BTCUSDT", side: "sell", type: "market", quantity: 1 } });
  const m = signedParams(log[1]);
  assert.equal(m.type, "MARKET"); assert.equal(m.timeInForce, undefined); assert.equal(m.price, undefined);
});

test("binance_spot rejected cancel is an error with the secret redacted (wire)", async () => {
  const { client, log } = await connect(CREDS, () => ({ status: 400, body: { code: -2011, msg: `Unknown order sent. ${CREDS.api_secret}` } }));
  const res = await client.callTool({ name: "cancel_order", arguments: { order_id: "4", symbol: "LTCBTC" } });
  assert.equal(res.isError, true);
  assert.equal(log[0].init.method, "DELETE");
  assert.equal(signedParams(log[0]).orderId, "4");
  assert.ok(res.content[0].text.includes("Unknown order sent") && !res.content[0].text.includes(CREDS.api_secret));
});

test("binance_spot public market data is sent unsigned (wire)", async () => {
  const { client, log } = await connect(CREDS, (url) => (url.pathname.endsWith("/klines")
    ? { body: [[1499040000000, "0.0163", "0.8", "0.0157", "0.0158", "148976.1", 1499644799999, "1", 1, "1", "1", "0"]] }
    : { body: { symbol: "BNBBTC", lastPrice: "4.000002", bidPrice: "4.0", askPrice: "4.000002", volume: "8913.3" } }));
  const c = await client.callTool({ name: "get_candles", arguments: { symbol: "BNBBTC", interval: "1d", limit: 5 } });
  assert.equal(c.isError, false);
  assert.equal(c.structuredContent.candles[0].close, 0.0158);
  assert.equal(log[0].url.search, "?symbol=BNBBTC&interval=1d&limit=5");
  const t = await client.callTool({ name: "get_ticker", arguments: { symbol: "BNBBTC" } });
  assert.equal(t.structuredContent.last, "4.000002");
  assert.equal(log[1].url.search, "?symbol=BNBBTC");
});
