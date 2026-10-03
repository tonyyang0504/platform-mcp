import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/producthunt.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { token: "ph-dev-token-123" }, 50, "test", fakeFetch(handler), a.envelope));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("producthunt: read_comments posts a GraphQL query with variables (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { data: { post: { comments: { totalCount: 1, edges: [{ node: { id: "c1", body: "Nice", createdAt: "2026-09-20T00:00:00Z", user: { username: "kate" } } }] } } } } }; });
  const res = await client.callTool({ name: "read_comments", arguments: { post_id: "123" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.comments[0].author, "kate");
  assert.equal(seen.url.href, "https://api.producthunt.com/v2/api/graphql");
  assert.deepEqual(JSON.parse(seen.init.body).variables, { id: "123", first: 20 });
  assert.equal(seen.init.headers.Authorization, "Bearer ph-dev-token-123");
});
