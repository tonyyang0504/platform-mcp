import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/banggood_dropship.json", import.meta.url), "utf8"));

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { app_id: "APPID", app_secret: "sec" }, 50, "test", fakeFetch(handler), SPEC.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("GET token login, access_token query, order + tracking (wire)", async () => {
  const calls = [];
  const client = await connect((url) => {
    calls.push(url);
    if (url.pathname === "/getAccessToken") return { body: { code: 0, access_token: "TOK", expires_in: 7200 } };
    if (url.pathname === "/order/getOrderInfo") return { body: { code: 0, sale_record_id_list: [{ sale_record_id: "S1", order_list: [{ order_id: "98765", status: "Processing", currency: "USD", total_amount: "25.10" }] }] } };
    return { body: { code: 0, track_info: [{ event: "Shipped from CN", time: "2016-10-01 10:00:00" }] } };
  });
  const res = await client.callTool({ name: "get_order", arguments: { id: "S1" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "98765");
  assert.equal(res.structuredContent.total_amount, "25.10");
  assert.equal(calls[0].searchParams.get("app_secret"), "sec");
  assert.equal(calls[1].searchParams.get("access_token"), "TOK");
  assert.equal(calls[1].searchParams.get("sale_record_id"), "S1");
  const tr = await client.callTool({ name: "track", arguments: { order_id: "98765" } });
  assert.equal(tr.structuredContent.events[0].event, "Shipped from CN");
});
