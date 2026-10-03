import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/mastodon.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

// The instance host is a per-install config field: exercise the real credential path (environment + global fetch)
// rather than an injected transport, because `@instance` resolves from the resolved credentials.
process.env.PLATFORM_MCP_MASTODON_TOKEN = "T";
process.env.PLATFORM_MCP_MASTODON_INSTANCE = "mastodon.example";

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("mastodon publish_text goes to the configured instance with a bearer token (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { id: "1", url: "https://mastodon.example/@me/1", created_at: "2026-09-24T00:00:00Z", content: "<p>hi</p>" } }; });
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["analytics_post", "delete", "me", "publish_text", "read_comments", "read_mentions", "reply_comment"]);
  const res = await client.callTool({ name: "publish_text", arguments: { text: "hi", reply_to: "9" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "1");
  assert.equal(seen.url.href, "https://mastodon.example/api/v1/statuses");
  assert.deepEqual(JSON.parse(seen.init.body), { status: "hi", in_reply_to_id: "9" });
  assert.equal(seen.init.headers.Authorization, "Bearer T");
});

test("mastodon read_comments maps context.descendants (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { ancestors: [], descendants: [{ id: "2", content: "<p>reply</p>", created_at: "2026-09-24T00:00:00Z", account: { acct: "zsc" } }] } }; });
  const res = await client.callTool({ name: "read_comments", arguments: { post_id: "1" } });
  assert.equal(res.isError, false);
  assert.equal(seen.href, "https://mastodon.example/api/v1/statuses/1/context");
  assert.equal(res.structuredContent.comments[0].author, "zsc");
  assert.equal(res.structuredContent.next_page, null);
});
