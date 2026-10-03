import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/trading/polymarket.json", import.meta.url), "utf8"));
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
test("polymarket offers public reads only (wire)", async () => {
  const { client } = await connect({}, () => ({ body: {} }));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_ticker", "list_markets", "me"]);
});

test("polymarket list_markets pages with limit/offset and ticker reads by slug (wire)", async () => {
  const { client, log } = await connect({}, (url) => (url.pathname === "/markets"
    ? { body: [{ id: "4464920", slug: "unl-nor", question: "Q?", conditionId: "0x80", volume: "1" }] }
    : { body: { slug: "unl-nor", bestBid: 0.57, bestAsk: 0.58, lastTradePrice: 0.58, volume24hr: 9 } }));
  const m = await client.callTool({ name: "list_markets", arguments: { page: 2, limit: 5 } });
  assert.equal(m.structuredContent.markets[0].symbol, "unl-nor");
  assert.equal(log[0].url.searchParams.get("offset"), "5");
  assert.equal(log[0].url.searchParams.get("closed"), "false");
  const t = await client.callTool({ name: "get_ticker", arguments: { symbol: "unl-nor" } });
  assert.equal(t.structuredContent.ask, 0.58);
  assert.equal(log[1].url.pathname, "/markets/slug/unl-nor");
});

test("polymarket unknown slug is an isError result (wire)", async () => {
  const { client } = await connect({}, () => ({ status: 404, body: { error: "id not found" } }));
  const res = await client.callTool({ name: "get_ticker", arguments: { symbol: "nope" } });
  assert.equal(res.isError, true);
});
