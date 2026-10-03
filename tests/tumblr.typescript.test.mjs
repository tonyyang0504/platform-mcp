import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/tumblr.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_key: "consumer-key", blog_identifier: "staff.tumblr.com" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("tumblr offers the API-key level verbs only and analytics_post reads one post by id (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { meta: { status: 200, msg: "OK" }, response: { blog: { name: "staff" }, posts: [{ id: 1234567890, id_string: "1234567890", post_url: "https://staff.tumblr.com/post/1234567890", type: "text", date: "2026-09-24 09:00:00 GMT", note_count: 321 }], total_posts: 1 } } }; });
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["analytics_post", "me"]);
  const res = await client.callTool({ name: "analytics_post", arguments: { post_id: "1234567890" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.post_id, "1234567890");
  assert.equal(res.structuredContent.notes, 321);
  assert.equal(res.structuredContent.url, "https://staff.tumblr.com/post/1234567890");
  assert.equal(seen.url.origin + seen.url.pathname, "https://api.tumblr.com/v2/blog/staff.tumblr.com/posts");
  assert.equal(seen.url.searchParams.get("id"), "1234567890");
  assert.equal(seen.url.searchParams.get("api_key"), "consumer-key");
  assert.equal(seen.init.headers.Authorization, undefined);
});

test("tumblr me describes the configured blog and a rejected key is an auth_error (wire)", async () => {
  let calls = 0;
  const client = await connect(() => (++calls === 1 ? { body: { meta: { status: 200, msg: "OK" }, response: { blog: { name: "staff", title: "Tumblr Staff" } } } } : { status: 401, body: { meta: { status: 401, msg: "Unauthorized" }, response: [] } }));
  const ok = await client.callTool({ name: "me", arguments: {} });
  assert.equal(ok.isError, false);
  assert.equal(ok.structuredContent.account.response.blog.name, "staff");
  const bad = await client.callTool({ name: "me", arguments: {} });
  assert.equal(bad.isError, true);
  assert.equal(bad.structuredContent.error, "auth_error");
});
