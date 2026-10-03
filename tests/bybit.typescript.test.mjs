import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/trading/bybit.json", import.meta.url), "utf8"));
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
const CREDS = { api_key: "KEY-bybit-abcdef", api_secret: "SECRET-bybit-abcdef" };
const expectSign = (e) => {
  const h = e.init.headers; const q = e.url.href.includes("?") ? e.url.href.split("?")[1] : "";
  assert.equal(h["X-BAPI-SIGN"], hmacHex(CREDS.api_secret, `${h["X-BAPI-TIMESTAMP"]}${CREDS.api_key}5000${q}${e.init.body ?? ""}`));
  assert.equal(h["X-BAPI-API-KEY"], CREDS.api_key);
};

test("bybit GET signs the query and maps tickers (wire)", async () => {
  const { client, log } = await connect({ ...CREDS, category: "linear" }, () => ({ body: { retCode: 0, retMsg: "OK", result: { category: "linear", list: [{ symbol: "BTCUSDT", lastPrice: "83553.4", bid1Price: "83553.3", ask1Price: "83553.4", volume24h: "6590.8" }] } } }));
  const res = await client.callTool({ name: "get_ticker", arguments: { symbol: "BTCUSDT" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.bid, "83553.3");
  assert.equal(log[0].url.searchParams.get("category"), "linear");
  expectSign(log[0]);
});

test("bybit place_order signs the exact JSON body (wire)", async () => {
  const { client, log } = await connect({ ...CREDS, category: "spot" }, () => ({ body: { retCode: 0, retMsg: "OK", result: { orderId: "1321", orderLinkId: "" } } }));
  const res = await client.callTool({ name: "place_order", arguments: { symbol: "BTCUSDT", side: "buy", type: "limit", quantity: 0.002, price: 60000 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.order_id, "1321");
  assert.deepEqual(JSON.parse(log[0].init.body), { category: "spot", symbol: "BTCUSDT", side: "Buy", orderType: "Limit", qty: "0.002", price: "60000", marketUnit: "baseCoin" });
  expectSign(log[0]);
});

test("bybit retCode != 0 is an error (wire)", async () => {
  const { client } = await connect({ ...CREDS, category: "linear" }, () => ({ body: { retCode: 110007, retMsg: "ab not enough for new order" } }));
  const res = await client.callTool({ name: "place_order", arguments: { symbol: "BTCUSDT", side: "buy", type: "market", quantity: 1 } });
  assert.equal(res.isError, true);
  assert.ok(res.content[0].text.includes("not enough") && !res.content[0].text.includes(CREDS.api_secret));
});

test("bybit candles map the interval and read newest-first rows (wire)", async () => {
  const { client, log } = await connect({ ...CREDS, category: "linear" }, () => ({ body: { retCode: 0, retMsg: "OK", result: { list: [["1790262000000", "1", "2", "0.5", "1.5", "10", "15"]] } } }));
  const res = await client.callTool({ name: "get_candles", arguments: { symbol: "BTCUSDT", interval: "1d" } });
  assert.equal(res.structuredContent.candles[0].high, 2);
  assert.equal(log[0].url.searchParams.get("interval"), "D");
  assert.equal(log[0].url.searchParams.get("limit"), "100");
});
