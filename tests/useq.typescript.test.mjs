import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/trading/useq.json", import.meta.url), "utf8"));
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
const CREDS = { api_key: "PKTESTKEY123456", api_secret: "SECRET-alpaca-abcdef" };

test("useq defaults to the paper host and sends key headers (wire)", async () => {
  const { client, log } = await connect(CREDS, () => ({ body: { id: "a1", status: "accepted", symbol: "AAPL", qty: "3" } }));
  const res = await client.callTool({ name: "place_order", arguments: { symbol: "AAPL", side: "buy", type: "market", quantity: 3 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.order_id, "a1");
  assert.equal(log[0].url.origin, "https://paper-api.alpaca.markets");
  assert.deepEqual(JSON.parse(log[0].init.body), { symbol: "AAPL", qty: "3", side: "buy", type: "market", time_in_force: "day" });
  assert.equal(log[0].init.headers["APCA-API-KEY-ID"], CREDS.api_key);
  assert.equal(log[0].init.headers["APCA-API-SECRET-KEY"], CREDS.api_secret);
});

test("useq cancel answers 204 and orders list maps (wire)", async () => {
  const { client, log } = await connect(CREDS, (url, init) => (init.method === "DELETE" ? { status: 204 } : { body: [{ id: "o1", symbol: "AAPL", side: "buy", type: "limit", status: "new", qty: "1", filled_qty: "0", limit_price: "150" }] }));
  const c = await client.callTool({ name: "cancel_order", arguments: { order_id: "o1" } });
  assert.equal(c.isError, false);
  assert.equal(c.structuredContent.status, "cancel_requested");
  assert.equal(log[0].url.pathname, "/v2/orders/o1");
  const l = await client.callTool({ name: "list_orders", arguments: { status: "open" } });
  assert.equal(l.structuredContent.orders[0].price, "150");
  assert.equal(log[1].url.searchParams.get("status"), "open");
});

test("useq rejection is redacted (wire)", async () => {
  const { client } = await connect(CREDS, () => ({ status: 422, body: { code: 40010001, message: `invalid qty ${CREDS.api_secret}` } }));
  const res = await client.callTool({ name: "place_order", arguments: { symbol: "AAPL", side: "sell", type: "market", quantity: 0 } });
  assert.equal(res.isError, true);
  assert.ok(!res.content[0].text.includes(CREDS.api_secret));
});
