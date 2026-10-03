import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/github.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { token: "ghp_testsecret123" }, 50, "test", fakeFetch(handler), a.envelope));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("github: analytics_post maps discussion counts (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { data: { node: { id: "D_1", url: "https://github.com/o/r/discussions/1", comments: { totalCount: 3 }, reactions: { totalCount: 7 } } } } }; });
  const res = await client.callTool({ name: "analytics_post", arguments: { post_id: "D_1" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.comments, 3);
  assert.equal(res.structuredContent.reactions, 7);
  assert.equal(seen.url.href, "https://api.github.com/graphql");
  assert.deepEqual(JSON.parse(seen.init.body).variables, { id: "D_1" });
  assert.equal(seen.init.headers.Authorization, "Bearer ghp_testsecret123");
});

test("github: GraphQL errors with null data are an error result (wire)", async () => {
  const client = await connect(() => ({ body: { data: null, errors: [{ message: "Could not resolve to a node" }] } }));
  const res = await client.callTool({ name: "delete", arguments: { post_id: "x" } });
  assert.equal(res.isError, true);
});
