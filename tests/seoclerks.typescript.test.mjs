import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/seoclerks.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (r.raw !== undefined ? r.raw : JSON.stringify(r.body ?? {})) }; };
const ROW = { id: "105824", title: "Looking for a gaming logo", service_url: "https://www.seoclerks.com/job/youtube/105824/x", price: "7", buyer_username: "gamerx" };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, {}, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("seoclerks: search asks for wtb jobs as JSON (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: [ROW] }; });
  const res = await client.callTool({ name: "search_postings", arguments: { query: "logo", limit: 5 } });
  assert.equal(res.isError, false);
  assert.equal(seen.origin + seen.pathname, "https://www.seoclerks.com/api");
  assert.equal(seen.searchParams.get("dt"), "wtb");
  assert.equal(seen.searchParams.get("f"), "json");
  assert.equal(seen.searchParams.get("s"), "logo");
  assert.equal(seen.searchParams.get("am"), "5");
  assert.equal(res.structuredContent.postings[0].buyer, "gamerx");
});

test("seoclerks: limit is capped at 40 (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: [ROW] }; });
  const res = await client.callTool({ name: "search_postings", arguments: { query: "logo", limit: 100 } });
  assert.equal(res.isError, false);
  assert.equal(seen.searchParams.get("am"), "40");
});
