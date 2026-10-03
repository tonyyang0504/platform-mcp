import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/automotive/twodehands.json", import.meta.url), "utf8"));
const CREDS = { client_id: "tdh-client", client_secret: "tdh-secret-0123456789" };
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

test("twodehands: same API on api.2dehands.be (wire)", async () => {
  const client = await connect((url) => url.hostname === "auth.2dehands.be" ? { body: { access_token: "tdh-access", expires_in: 86400 } } : { body: { _embedded: { "mp:search-result": [{ itemId: "m1", title: "Corsa" }] }, totalCount: 1 } });
  const res = await client.callTool({ name: "search_listings", arguments: { query: "corsa" } });
  assert.equal(res.isError, false); assert.equal(res.structuredContent.listings[0].id, "m1");
  assert.ok(client.seen.some((x) => x.url.hostname === "api.2dehands.be" && x.url.pathname === "/v1/search"));
});
