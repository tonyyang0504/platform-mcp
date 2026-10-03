import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/automotive/autotrader_uk.json", import.meta.url), "utf8"));
const CREDS = { key: "at-key-0123456789", secret: "at-secret-0123456789", advertiser_id: "123456" };
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

test("autotrader_uk: form login, search and valuation (wire)", async () => {
  const client = await connect((url) => {
    if (url.pathname === "/authenticate") return { body: { access_token: "at-access-token", expires_at: "2026-10-01T13:06:30Z" } };
    if (url.pathname === "/search") return { body: { results: [{ vehicle: { make: "Hyundai", model: "i10", odometerReadingMiles: 20703 }, advertiser: { name: "Dealer", location: { town: "MANCHESTER" } }, adverts: { retailAdverts: { suppliedPrice: { amountGBP: 10200 } } }, metadata: { searchId: "202606259954923" } }], totalResults: 1 } };
    return { body: { results: [{ vehicle: { make: "Volkswagen" }, valuations: { trade: { amountGBP: 8446 }, private: { amountGBP: 9380 }, retail: { amountGBP: 10802 } } }] } };
  });
  const res = await client.callTool({ name: "search_listings", arguments: { make: "Hyundai", condition: "used" } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.equal(res.structuredContent.listings[0].id, "202606259954923"); assert.equal(res.structuredContent.listings[0].price, 10200);
  const login = client.seen[0];
  assert.equal(login.url.pathname, "/authenticate"); assert.match(String(login.init.body), /key=at-key-0123456789/);
  const s = client.seen.find((x) => x.url.pathname === "/search");
  assert.equal(hdr(s.init, "Authorization"), "Bearer at-access-token");
  assert.equal(s.url.searchParams.get("advertiserId"), "123456"); assert.equal(s.url.searchParams.get("ownershipCondition"), "Used");
  const val = await client.callTool({ name: "get_valuation", arguments: { vin: "WVWZZZE1ZMP081246", mileage: 8000 } });
  assert.equal(val.isError, false); assert.equal(val.structuredContent.mid, 9380); assert.equal(val.structuredContent.currency, "GBP");
  const v = client.seen.find((x) => x.url.pathname === "/vehicles");
  assert.equal(v.url.searchParams.get("valuations"), "true"); assert.equal(v.url.searchParams.get("odometerReadingMiles"), "8000");
});
