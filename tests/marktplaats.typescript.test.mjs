import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/automotive/marktplaats.json", import.meta.url), "utf8"));
const CREDS = { client_id: "mp-client", client_secret: "mp-secret-0123456789", category_id: "91" };
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

test("marktplaats: search with a client token (wire)", async () => {
  const client = await connect((url) => url.hostname === "auth.marktplaats.nl"
    ? { body: { access_token: "mp-access", expires_in: 86400 } }
    : { body: { _embedded: { "mp:search-result": [{ itemId: "m459", title: "Golf", seller: { sellerName: "Autobedrijf X" }, _links: { "mp:advertisement-website-link": { href: "http://link.marktplaats.nl/m459" } } }] }, totalCount: 61 } });
  const res = await client.callTool({ name: "search_listings", arguments: { query: "golf", page: 2, limit: 30 } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.equal(res.structuredContent.listings[0].url, "http://link.marktplaats.nl/m459"); assert.equal(res.structuredContent.total, 61);
  const s = client.seen.find((x) => x.url.pathname === "/v1/search");
  assert.equal(hdr(s.init, "Authorization"), "Bearer mp-access");
  assert.equal(s.url.searchParams.get("offset"), "30"); assert.equal(s.url.searchParams.get("categoryId"), "91");
});
