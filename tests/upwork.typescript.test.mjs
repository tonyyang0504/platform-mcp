import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/upwork.json", import.meta.url), "utf8"));
const CREDS = { client_id: "upw-cid", client_secret: "upw-secret-123456", refresh_token: "oauth2v2_refresh_abcdef" };
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const hdr = (init, name) => { const h = init.headers ?? {}; if (typeof h.get === "function") return h.get(name); const k = Object.keys(h).find((x) => x.toLowerCase() === name.toLowerCase()); return k ? h[k] : undefined; };

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", fakeFetch(handler), a.envelope));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("upwork: search mints a token then posts the GraphQL filter (wire)", async () => {
  const calls = [];
  const client = await connect((url, init) => {
    calls.push({ url, init });
    if (url.href.startsWith("https://www.upwork.com/api/v3/oauth2/token")) return { body: { access_token: "oauth2v2_access_1", expires_in: 86400 } };
    return { body: { data: { marketplaceJobPostingsSearch: { totalCount: 1, edges: [{ node: { id: "2056488576136638272", title: "PHP developer", publishedDateTime: "2026-09-24T10:00:00Z" } }] } } } };
  });
  const res = await client.callTool({ name: "search_postings", arguments: { query: "php", limit: 5 } });
  assert.equal(res.isError, false);
  const g = calls.find((c) => c.url.href === "https://api.upwork.com/graphql");
  assert.equal(hdr(g.init, "Authorization"), "Bearer oauth2v2_access_1");
  const body = JSON.parse(g.init.body);
  assert.deepEqual(body.variables, { filter: { searchExpression_eq: "php", pagination_eq: { after: "0", first: 5 } } });
  assert.equal(res.structuredContent.postings[0].id, "2056488576136638272");
  assert.equal(res.structuredContent.total, 1);
});

test("upwork: null data with errors is an isError result (wire)", async () => {
  const client = await connect((url) => url.href.includes("oauth2/token") ? { body: { access_token: "oauth2v2_access_1", expires_in: 86400 } } : { body: { data: null, errors: [{ message: "Permission denied" }] } });
  const res = await client.callTool({ name: "get_posting", arguments: { id: "1" } });
  assert.equal(res.isError, true);
});
