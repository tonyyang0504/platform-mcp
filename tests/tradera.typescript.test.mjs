import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/automotive/tradera.json", import.meta.url), "utf8"));
const CREDS = { app_id: "1234", app_key: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" };
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

test("tradera: get item with app headers (wire)", async () => {
  const client = await connect(() => ({ body: { id: 567890, shortDescription: "Volvo 240", buyItNowPrice: 25000, itemLink: "https://www.tradera.com/item/1/567890" } }));
  const res = await client.callTool({ name: "get_listing", arguments: { listing_id: "567890" } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.equal(res.structuredContent.id, "567890"); assert.equal(res.structuredContent.currency, "SEK");
  const s = client.seen[0];
  assert.equal(s.url.pathname, "/v4/items/567890");
  assert.equal(hdr(s.init, "X-App-Id"), "1234"); assert.equal(hdr(s.init, "X-App-Key"), "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee");
});
