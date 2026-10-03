import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/instagram.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

process.env.PLATFORM_MCP_INSTAGRAM_ACCESS_TOKEN = "IG-TOKEN";
process.env.PLATFORM_MCP_INSTAGRAM_IG_USER_ID = "17841405822304914";

test("instagram reply_comment posts to /{comment_id}/replies (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { id: "17873440459141029" } }; });
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["analytics_post", "me", "read_comments", "read_mentions", "reply_comment"]);
  const res = await client.callTool({ name: "reply_comment", arguments: { comment_id: "17870913679156914", text: "Thanks!" } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.href, "https://graph.facebook.com/v26.0/17870913679156914/replies");
  assert.deepEqual(JSON.parse(seen.init.body), { message: "Thanks!" });
  assert.equal(seen.init.headers.Authorization, "Bearer IG-TOKEN");
});

test("instagram analytics_post reads media counts (wire)", async () => {
  const client = await connect(() => ({ body: { id: "18038", like_count: 5, comments_count: 2 } }));
  const res = await client.callTool({ name: "analytics_post", arguments: { post_id: "18038" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.likes, 5);
  assert.equal(res.structuredContent.comments, 2);
});
