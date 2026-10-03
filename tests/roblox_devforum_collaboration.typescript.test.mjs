import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/roblox_devforum_collaboration.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const TOPIC = { id: 4884226, title: "[HIRING] Scripter", created_at: "2026-09-20T16:07:54.000Z", excerpt: "…", category_id: 82 };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, {}, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("roblox_devforum_collaboration: search scopes the query to category 82 (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { topics: [TOPIC], posts: [] } }; });
  const res = await client.callTool({ name: "search_postings", arguments: { query: "scripter", page: 2 } });
  assert.equal(res.isError, false);
  assert.equal(seen.origin + seen.pathname, "https://devforum.roblox.com/search.json");
  assert.equal(seen.searchParams.get("q"), "scripter category:82 order:latest");
  assert.equal(seen.searchParams.get("page"), "2");
  assert.equal(res.structuredContent.postings[0].id, "4884226");
});

test("roblox_devforum_collaboration: get_posting reads the topic creator (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { ...TOPIC, details: { created_by: { username: "StudioOwner" } }, post_stream: { posts: [{ cooked: "<p>x</p>" }] } } }; });
  const res = await client.callTool({ name: "get_posting", arguments: { id: "4884226" } });
  assert.equal(seen.pathname, "/t/4884226.json");
  assert.equal(res.structuredContent.buyer, "StudioOwner");
});
