import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/automotive/mobilede.json", import.meta.url), "utf8"));
const CREDS = { username: "dealer-api", password: "md-pass-1234567" };
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

test("mobilede: search with basic auth and the JSON media type (wire)", async () => {
  const client = await connect(() => ({ body: { total: 5, ads: [{ mobileAdId: "15012", make: "AUDI", model: "A4", mileage: 500, price: { consumerPriceGross: "1000.00", currency: "EUR" } }] } }));
  const res = await client.callTool({ name: "search_listings", arguments: { make: "AUDI", year_min: 2018, condition: "used" } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.equal(res.structuredContent.listings[0].id, "15012"); assert.equal(res.structuredContent.total, 5);
  const s = client.seen[0];
  assert.equal(s.url.pathname, "/search-api/search");
  assert.equal(s.url.searchParams.get("classification"), "refdata/classes/Car/makes/AUDI");
  assert.equal(s.url.searchParams.get("firstRegistrationDate.min"), "2018-01");
  assert.equal(s.url.searchParams.get("condition"), "USED");
  assert.equal(hdr(s.init, "Authorization"), "Basic " + Buffer.from("dealer-api:md-pass-1234567").toString("base64"));
  assert.equal(hdr(s.init, "Accept"), "application/vnd.de.mobile.api+json");
});
