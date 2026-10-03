import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/trading/binance.json", import.meta.url), "utf8"));
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
  return Object.fromEntries(signed.split("&").map((p) => p.split("=")));
};

test("binance offers all eight trading verbs (wire)", async () => {
  const { client } = await connect(CREDS, () => ({ body: {} }));
  const { tools } = await client.listTools();
  assert.equal(tools.length, 8);
  assert.ok(tools.find((t) => t.name === "place_order").description.includes("testnet.binancefuture.com"));
});

test("binance klines are signed and mapped from positional rows (wire)", async () => {
  const { client, log } = await connect(CREDS, () => ({ body: [[1790262000000, "83628.2", "83810.6", "83440.4", "83769.5", "2526.082", 1790265599999, "1", 1, "1", "1", "0"]] }));
  const res = await client.callTool({ name: "get_candles", arguments: { symbol: "BTCUSDT", interval: "1h", limit: 5 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.candles[0].close, 83769.5);
  assert.equal(res.structuredContent.candles[0].time, "1790262000000"); // numbers and a string time, as the vocabulary types them
  assert.equal(log[0].url.pathname, "/fapi/v1/klines");
  const p = signedParams(log[0]);
  assert.deepEqual([p.symbol, p.interval, p.limit], ["BTCUSDT", "1h", "5"]);
});

test("binance place_order and balances (wire)", async () => {
  const { client, log } = await connect(CREDS, (url) => (url.pathname === "/fapi/v3/balance"
    ? { body: [{ asset: "USDT", balance: "122.3", availableBalance: "23.7", crossWalletBalance: "23.7", crossUnPnl: "0" }] }
    : { body: { orderId: 22542179, status: "NEW", symbol: "BTCUSDT", origQty: "10", executedQty: "0" } }));
  const res = await client.callTool({ name: "place_order", arguments: { symbol: "BTCUSDT", side: "sell", type: "market", quantity: 10 } });
  assert.equal(res.structuredContent.order_id, "22542179");
  const p = signedParams(log[0]);
  assert.deepEqual([p.side, p.type, p.quantity, p.timeInForce], ["SELL", "MARKET", "10", undefined]);
  const bal = await client.callTool({ name: "get_balances", arguments: {} });
  assert.equal(bal.structuredContent.balances[0].available, "23.7");
});

test("binance error body is redacted (wire)", async () => {
  const { client } = await connect(CREDS, () => ({ status: 400, body: { code: -2019, msg: `Margin is insufficient. ${CREDS.api_secret}` } }));
  const res = await client.callTool({ name: "place_order", arguments: { symbol: "BTCUSDT", side: "buy", type: "market", quantity: 1 } });
  assert.equal(res.isError, true);
  assert.ok(res.content[0].text.includes("Margin is insufficient") && !res.content[0].text.includes(CREDS.api_secret));
});
