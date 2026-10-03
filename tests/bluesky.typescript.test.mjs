import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/bluesky.json", import.meta.url), "utf8"));
const DID = "did:plc:z72i7hdynmk6r22z27h6tvur";
const POST = `at://${DID}/app.bsky.feed.post/3k2yihcrp2c2a`;
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

// session auth: the runtime logs in with the app password (environment credentials) and caches the accessJwt
process.env.PLATFORM_MCP_BLUESKY_IDENTIFIER = "alice.bsky.social";
process.env.PLATFORM_MCP_BLUESKY_PASSWORD = "app-pass";
process.env.PLATFORM_MCP_BLUESKY_DID = DID;

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("bluesky publish_text logs in via createSession then posts a record with the JWT (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => {
    seen.push({ url, init });
    if (url.pathname === "/xrpc/com.atproto.server.createSession") return { body: { accessJwt: "JWT1", refreshJwt: "R", handle: "alice.bsky.social", did: DID } };
    return { body: { uri: POST, cid: "bafy" } };
  });
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["analytics_post", "me", "publish_text", "read_comments", "read_mentions"]);
  const res = await client.callTool({ name: "publish_text", arguments: { text: "hi" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, POST);
  assert.equal(seen[0].url.href, "https://bsky.social/xrpc/com.atproto.server.createSession");
  assert.deepEqual(JSON.parse(seen[0].init.body), { identifier: "alice.bsky.social", password: "app-pass" });
  assert.equal(seen[1].url.href, "https://bsky.social/xrpc/com.atproto.repo.createRecord");
  const body = JSON.parse(seen[1].init.body);
  assert.equal(body.repo, DID); assert.equal(body.collection, "app.bsky.feed.post");
  assert.equal(body.record.$type, "app.bsky.feed.post"); assert.equal(body.record.text, "hi"); assert.match(body.record.createdAt, /^\d{4}-\d{2}-\d{2}T.*Z$/);
  assert.equal(seen[1].init.headers.Authorization, "Bearer JWT1");
});

test("bluesky read_comments maps thread.replies (wire)", async () => {
  let last;
  const client = await connect((url) => {
    last = url;
    if (url.pathname === "/xrpc/com.atproto.server.createSession") return { body: { accessJwt: "JWT1", refreshJwt: "R", handle: "alice.bsky.social", did: DID } };
    return { body: { thread: { post: { uri: POST }, replies: [{ post: { uri: "at://did:plc:bob/app.bsky.feed.post/1", author: { did: "did:plc:bob", handle: "bob.bsky.social" }, record: { text: "nice" }, indexedAt: "2026-09-24T00:00:00.000Z" } }] } } };
  });
  const res = await client.callTool({ name: "read_comments", arguments: { post_id: POST } });
  assert.equal(res.isError, false);
  assert.equal(last.pathname, "/xrpc/app.bsky.feed.getPostThread");
  assert.equal(last.searchParams.get("uri"), POST);
  assert.equal(res.structuredContent.comments[0].author, "bob.bsky.social");
  assert.equal(res.structuredContent.comments[0].text, "nice");
  assert.equal(res.structuredContent.next_page, null);
});
