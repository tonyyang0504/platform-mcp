import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/trading/hyperliquid_spot.json", import.meta.url), "utf8"));
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
const WALLET = "0x2222222222222222222222222222222222222222";

test("hyperliquid_spot offers read verbs only (wire)", async () => {
  const { client } = await connect({}, () => ({ body: {} }));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_balances", "get_ticker", "list_markets", "list_orders", "me"]);
  assert.ok(tools.every((t) => t.annotations.readOnlyHint === true));
});

test("hyperliquid_spot list_markets posts spotMeta (wire)", async () => {
  const { client, log } = await connect({}, () => ({ body: { tokens: [], universe: [{ name: "PURR/USDC", tokens: [1, 0], index: 0, isCanonical: true }] } }));
  const res = await client.callTool({ name: "list_markets", arguments: {} });
  assert.equal(res.structuredContent.markets[0].symbol, "PURR/USDC");
  assert.deepEqual(JSON.parse(log[0].init.body), { type: "spotMeta" });
});

test("hyperliquid_spot balances and open orders use the configured address (wire)", async () => {
  const { client, log } = await connect({ wallet_address: WALLET }, (_u, init) => (JSON.parse(init.body).type === "openOrders"
    ? { body: [{ coin: "PURR/USDC", limitPx: "0.2", oid: 7, side: "B", sz: "100", timestamp: 1 }] }
    : { body: { balances: [{ coin: "USDC", token: 0, hold: "0.0", total: "14.6", entryNtl: "0.0" }] } }));
  const b = await client.callTool({ name: "get_balances", arguments: {} });
  assert.equal(b.structuredContent.balances[0].total, "14.6");
  assert.deepEqual(JSON.parse(log[0].init.body), { type: "spotClearinghouseState", user: WALLET });
  const o = await client.callTool({ name: "list_orders", arguments: {} });
  assert.equal(o.structuredContent.orders[0].order_id, "7");
});
