import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/automotive/autostrefa_mx.json", import.meta.url), "utf8"));
const CREDS = {};
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

test("autostrefa_mx: public inventory search and envelope error (wire)", async () => {
  const client = await connect((url) => url.pathname === "/api/public/inventory"
    ? { body: { success: true, data: [{ id: 83890829, titulo: "Defender", marca: "Land Rover", "año": 2024, precio: 1849900, kilometraje: 35035 }], meta: { total: 45 } } }
    : { body: { success: false, data: null, error: "Vehiculo no encontrado" } });
  const res = await client.callTool({ name: "search_listings", arguments: { make: "Land Rover", limit: 10 } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  const row = res.structuredContent.listings[0];
  assert.equal(row.year, 2024); assert.equal(row.currency, "MXN"); assert.equal(res.structuredContent.total, 45);
  assert.equal(client.seen[0].url.searchParams.get("marca"), "Land Rover"); assert.equal(client.seen[0].url.searchParams.get("per_page"), "10");
  const bad = await client.callTool({ name: "get_listing", arguments: { listing_id: "nope" } });
  assert.equal(bad.isError, true);
});
