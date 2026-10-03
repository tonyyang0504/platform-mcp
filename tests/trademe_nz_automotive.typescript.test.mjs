import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/automotive/trademe_nz.json", import.meta.url), "utf8"));
const CREDS = { consumer_key: "4E0D082355116884742E5F33B8A199F411", consumer_secret: "160FCF77971DC92A38596288DB071A8CA5" };
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

test("trademe_nz automotive: used motors search (wire)", async () => {
  const client = await connect(() => ({ body: { TotalCount: 3, List: [{ ListingId: 4912345678, Title: "Toyota Corolla", Make: "Toyota", Model: "Corolla", Year: 2018, StartPrice: 15990, Odometer: 82000 }] } }));
  const res = await client.callTool({ name: "search_listings", arguments: { make: "Toyota", condition: "used", limit: 100 } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  const row = res.structuredContent.listings[0];
  assert.equal(row.id, "4912345678"); assert.equal(row.currency, "NZD"); assert.equal(row.mileage, 82000);
  const s = client.seen[0];
  assert.equal(s.url.pathname, "/v1/Search/Motors/Used.json");
  assert.equal(s.url.searchParams.get("rows"), "25"); assert.equal(s.url.searchParams.get("condition"), "Used");
  assert.equal(hdr(s.init, "Authorization"), "OAuth oauth_consumer_key=4E0D082355116884742E5F33B8A199F411, oauth_signature_method=PLAINTEXT, oauth_signature=160FCF77971DC92A38596288DB071A8CA5%26");
});

test("trademe_nz automotive: get_listing (wire)", async () => {
  const client = await connect(() => ({ body: { ListingId: 1, Title: "Ute", Body: "One owner" } }));
  const res = await client.callTool({ name: "get_listing", arguments: { listing_id: "1" } });
  assert.equal(res.structuredContent.description, "One owner");
  assert.equal(client.seen[0].url.pathname, "/v1/Listings/1.json");
});
