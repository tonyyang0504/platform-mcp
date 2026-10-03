import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/trading/deribit.json", import.meta.url), "utf8"));
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
const CREDS = { client_id: "CID-deribit-abc", client_secret: "SECRET-deribit-abcdef" };

test("deribit place_order routes to private/buy with Basic auth (wire)", async () => {
  const { client, log } = await connect(CREDS, () => ({ body: { jsonrpc: "2.0", result: { trades: [], order: { order_id: "ETH-1", order_state: "filled", instrument_name: "ETH-PERPETUAL", direction: "buy", amount: 40 } } } }));
  const res = await client.callTool({ name: "place_order", arguments: { symbol: "ETH-PERPETUAL", side: "buy", type: "market", quantity: 40 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.order_id, "ETH-1");
  assert.equal(log[0].url.pathname, "/api/v2/private/buy");
  assert.deepEqual(Object.fromEntries(log[0].url.searchParams), { instrument_name: "ETH-PERPETUAL", amount: "40", type: "market" });
  assert.equal(log[0].init.headers.Authorization, "Basic " + Buffer.from(`${CREDS.client_id}:${CREDS.client_secret}`).toString("base64"));
});

test("deribit list_markets and ticker (wire)", async () => {
  const { client, log } = await connect(CREDS, (url) => (url.pathname.endsWith("get_instruments")
    ? { body: { jsonrpc: "2.0", result: [{ instrument_name: "BTC-PERPETUAL", base_currency: "BTC", quote_currency: "USD", kind: "future", state: "open" }] } }
    : { body: { jsonrpc: "2.0", result: { instrument_name: "BTC-PERPETUAL", last_price: 83548, best_bid_price: 83547.5, best_ask_price: 83548, stats: { volume: 19890 } } } }));
  const m = await client.callTool({ name: "list_markets", arguments: {} });
  assert.equal(m.structuredContent.markets[0].symbol, "BTC-PERPETUAL");
  assert.equal(log[0].url.searchParams.get("currency"), "any");
  const t = await client.callTool({ name: "get_ticker", arguments: { symbol: "BTC-PERPETUAL" } });
  assert.equal(t.structuredContent.volume, 19890);
});

test("deribit JSON-RPC error (HTTP 400) is an isError result without the secret (wire)", async () => {
  const { client } = await connect(CREDS, () => ({ status: 400, body: { jsonrpc: "2.0", error: { code: 10009, message: `not_enough_funds ${CREDS.client_secret}` } } }));
  const res = await client.callTool({ name: "place_order", arguments: { symbol: "BTC-PERPETUAL", side: "sell", type: "limit", quantity: 10, price: 90000 } });
  assert.equal(res.isError, true);
  assert.ok(res.content[0].text.includes("not_enough_funds") && !res.content[0].text.includes(CREDS.client_secret));
});
