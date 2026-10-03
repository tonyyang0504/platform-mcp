import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/automotive/divar.json", import.meta.url), "utf8"));
const CREDS = { api_key: "divar-key-0123456789" };
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

test("divar: finder search body and get_post (wire)", async () => {
  const client = await connect((url) => url.pathname.startsWith("/v2/")
    ? { body: { posts: [{ token: "wZFdL0Vm", title: "cs55", city: "tehran", last_modified_at: "2024-11-26T11:59:25Z" }] } }
    : { body: { token: "AZir15UU", city: "tehran", data: { title: "206", price: { value: 1100000 }, images: ["https://s101.divarcdn.com/a.jpg"] } } });
  const res = await client.callTool({ name: "search_listings", arguments: { location: "tehran", model: "Pride 111 EX", year_min: 1400 } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.equal(res.structuredContent.listings[0].id, "wZFdL0Vm");
  const s = client.seen[0];
  assert.equal(hdr(s.init, "x-api-key"), "divar-key-0123456789");
  assert.deepEqual(JSON.parse(s.init.body), { category: "light", city: "tehran", query: { brand_model: ["Pride 111 EX"], production_year: { min: 1400 } } });
  const one = await client.callTool({ name: "get_listing", arguments: { listing_id: "AZir15UU" } });
  assert.equal(one.structuredContent.price, 1100000);
  assert.equal(client.seen[1].url.pathname, "/v1/open-platform/finder/post/AZir15UU");
});
