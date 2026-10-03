import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => ({ "content-type": "application/json" })[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(file, creds, handler) {
  const spec = JSON.parse(readFileSync(new URL(`../catalog/${file}`, import.meta.url), "utf8"));
  const a = spec.adapter;
  const server = buildServer(spec, new Transport(a.base_url, a.auth, { ...creds }, 50, "test", fakeFetch(handler), a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

function check(url, secret) {
  const q = Object.fromEntries(url.searchParams); const sig = q.sign; delete q.sign;
  assert.equal(sig, crypto.createHash("md5").update(secret + Object.keys(q).sort().map((k) => k + q[k]).join("") + secret).digest("hex").toUpperCase());
  return q;
}

test("taobao: GMT+8 timestamp and upper-case MD5 over sorted params (wire)", async () => {
  const realNow = Date.now; Date.now = () => 1790301600000;
  try {
    const creds = { app_key: "12345678", app_secret: "tb-secret-abcdef", session: "6100a1b2c3d4e5session" };
    let seen;
    const client = await connect("marketplaces/taobao.json", creds, (url) => { seen = url; return { body: { trades_sold_get_response: { total_results: 1, trades: { trade: [{ tid: 2231884277, payment: "200.07", orders: { order: [{ num_iid: 1489161932 }] } }] } } } }; });
    const res = await client.callTool({ name: "list_sales", arguments: { since: "2026-09-01" } });
    assert.equal(res.structuredContent.sales[0].id, "2231884277"); assert.equal(res.structuredContent.sales[0].product_id, "1489161932");
    const q = check(seen, creds.app_secret);
    assert.equal(q.timestamp, "2026-09-25 10:00:00"); assert.equal(q.method, "taobao.trades.sold.get"); assert.equal(q.session, creds.session);
    assert.equal(q.start_created, "2026-09-01 00:00:00");
  } finally { Date.now = realNow; }
});

test("taobao: error_response is an isError result", async () => {
  const client = await connect("marketplaces/taobao.json", { app_key: "1", app_secret: "s", session: "x" }, () => ({ body: { error_response: { code: 27, msg: "Invalid session" } } }));
  assert.equal((await client.callTool({ name: "me", arguments: {} })).isError, true);
});

