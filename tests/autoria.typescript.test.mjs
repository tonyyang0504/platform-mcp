import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/automotive/autoria.json", import.meta.url), "utf8"));
const CREDS = { api_key: "ria-key-0123456789abcdef", user_id: "12246211" };
const fakeFetch = (handler, seen) => async (url, init) => { const u = new URL(url); seen.push({ url: u, init }); const r = handler(u, init); return { status: r.status ?? 200, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null) }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const a = SPEC.adapter;
  const seen = [];
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", fakeFetch(handler, seen), a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  client.seen = seen;
  return client;
}
const hdr = (init, name) => { const h = init.headers || {}; const k = Object.keys(h).find((x) => x.toLowerCase() === name.toLowerCase()); return k ? h[k] : undefined; };

test("autoria: auto/info and the VIN valuation (wire)", async () => {
  const client = await connect((url) => url.pathname === "/auto/info"
    ? { body: { USD: 15500, title: "BMW X5", markName: "BMW", modelName: "X5", autoData: { autoId: 36756951, year: 2012 } } }
    : { body: { graphData: [{ date: "2026-08", price: { UAH: 1, USD: 4200 } }] } });
  const info = await client.callTool({ name: "get_listing", arguments: { listing_id: "36756951" } });
  assert.equal(info.isError, false); assert.equal(info.structuredContent.id, "36756951"); assert.equal(info.structuredContent.price, 15500);
  assert.equal(client.seen[0].url.searchParams.get("api_key"), "ria-key-0123456789abcdef");
  const val = await client.callTool({ name: "get_valuation", arguments: { vin: "TMBGP21U432674944" } });
  assert.equal(val.isError, false); assert.equal(val.structuredContent.raw.graphData[0].price.USD, 4200);
  const post = client.seen[1];
  assert.equal(post.url.pathname, "/auto/statistic-avarage-price/"); assert.equal(post.url.searchParams.get("user_id"), "12246211");
  assert.deepEqual(JSON.parse(post.init.body), { langId: 4, period: 365, params: { omniId: "TMBGP21U432674944" } });
});
