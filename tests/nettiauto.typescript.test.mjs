import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/automotive/nettiauto.json", import.meta.url), "utf8"));
const CREDS = { client_id: "nx-client", client_secret: "nx-secret-0123456789" };
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

test("nettiauto: client-credentials JWT as X-Access-Token, root-array search (wire)", async () => {
  const client = await connect((url) => url.hostname === "auth.nettix.fi"
    ? { body: { access_token: "eyJ.nettix.jwt", expires_in: 86400 } }
    : { body: [{ id: "12345678", make: { id: 4, name: "Volvo" }, model: { id: 55, name: "V60" }, year: 2019, price: 23900, kilometers: 88000, town: { id: 1, fi: "Helsinki", en: "Helsinki" } }] });
  const res = await client.callTool({ name: "search_listings", arguments: { query: "V60", make: "4", limit: 10 } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  const row = res.structuredContent.listings[0];
  assert.equal(row.make, "Volvo"); assert.equal(row.location, "Helsinki");
  const s = client.seen.find((x) => x.url.pathname === "/rest/car/search");
  assert.equal(hdr(s.init, "X-Access-Token"), "eyJ.nettix.jwt"); assert.equal(hdr(s.init, "Authorization"), undefined);
  assert.equal(s.url.searchParams.get("searchText"), "V60"); assert.equal(s.url.searchParams.get("rows"), "10");
});
