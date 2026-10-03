import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/lemmy.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const POST = { post_view: { post: { id: 123, name: "hello", ap_id: "https://lemmy.example/post/123", published: "2026-09-24T09:00:00.000Z" }, counts: { post_id: 123, comments: 4, score: 10, upvotes: 11, downvotes: 1 } } };

// `instance` and `community_id` are config fields resolved from transport.creds (login URL, tool paths, integer body field)
async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { username_or_email: "alice", password: "pw-secret", instance: "lemmy.example", community_id: "42" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("lemmy publish_text logs in on the configured instance, then posts with an integer community_id and the JWT (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => {
    seen.push({ url, init });
    if (url.pathname === "/api/v3/user/login") return { body: { jwt: "JWT1", registration_created: false, verify_email_sent: false } };
    return { body: POST };
  });
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["analytics_post", "delete", "me", "publish_image", "publish_text", "read_comments", "read_mentions"]);
  const res = await client.callTool({ name: "publish_text", arguments: { text: "hello" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "123");
  assert.equal(res.structuredContent.url, "https://lemmy.example/post/123");
  assert.equal(seen[0].url.href, "https://lemmy.example/api/v3/user/login");
  assert.deepEqual(JSON.parse(seen[0].init.body), { username_or_email: "alice", password: "pw-secret" });
  assert.equal(seen[1].url.href, "https://lemmy.example/api/v3/post");
  assert.deepEqual(JSON.parse(seen[1].init.body), { name: "hello", body: "hello", community_id: 42 });
  assert.equal(seen[1].init.headers.Authorization, "Bearer JWT1");
});

test("lemmy delete sends an integer post_id and publish_image sends the first image URL (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => {
    seen.push({ url, init });
    if (url.pathname === "/api/v3/user/login") return { body: { jwt: "JWT1", registration_created: false, verify_email_sent: false } };
    return { body: POST };
  });
  const del = await client.callTool({ name: "delete", arguments: { post_id: "123" } });
  assert.equal(del.isError, false);
  assert.equal(del.structuredContent.status, "deleted");
  assert.equal(seen[1].url.href, "https://lemmy.example/api/v3/post/delete");
  assert.deepEqual(JSON.parse(seen[1].init.body), { post_id: 123, deleted: true });
  const img = await client.callTool({ name: "publish_image", arguments: { text: "a picture", image_urls: ["https://img.example/a.png", "https://img.example/b.png"] } });
  assert.equal(img.isError, false);
  assert.deepEqual(JSON.parse(seen[2].init.body), { name: "a picture", url: "https://img.example/a.png", community_id: 42 });
  const bad = await client.callTool({ name: "delete", arguments: { post_id: "not-a-number" } });
  assert.equal(bad.isError, true);
  assert.equal(bad.structuredContent.error, "invalid_input");
  assert.equal(seen.length, 3);
});
