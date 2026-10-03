import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (r.raw ?? JSON.stringify(r.body ?? {})) }; };
const form = (body) => Object.fromEntries(new URLSearchParams(body));
async function connect(spec, handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(spec);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}
const names = async (spec) => (await (await connect(spec, () => ({}))).listTools()).tools.map((t) => t.name).sort();
const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/youtube.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_YOUTUBE_CLIENT_ID: "cid", PLATFORM_MCP_YOUTUBE_CLIENT_SECRET: "s", PLATFORM_MCP_YOUTUBE_REFRESH_TOKEN: "r" });
const TOKEN = "https://oauth2.googleapis.com/token";
const tok = { body: { access_token: "ya29.Y", expires_in: 3599 } };

test("youtube: tools (wire)", async () => {
  assert.deepEqual(await names(SPEC), ["analytics_post", "delete", "me", "read_comments", "reply_comment"]);
});

test("youtube: read_comments and reply_comment (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    if (url.href === TOKEN) return tok; seen.push({ url, init });
    if (url.pathname.endsWith("/commentThreads")) return { body: { items: [{ snippet: { topLevelComment: { id: "Ug1", snippet: { authorDisplayName: "Ann", textDisplay: "nice" } } } }] } };
    return { body: { id: "Ug1.r1", snippet: { publishedAt: "2026-09-24T00:00:00Z" } } };
  });
  const r1 = await client.callTool({ name: "read_comments", arguments: { post_id: "vid1" } });
  assert.equal(r1.structuredContent.comments[0].id, "Ug1");
  assert.equal(seen[0].url.searchParams.get("videoId"), "vid1");
  const r2 = await client.callTool({ name: "reply_comment", arguments: { comment_id: "Ug1", text: "thanks" } });
  assert.equal(r2.structuredContent.id, "Ug1.r1");
  assert.deepEqual(JSON.parse(seen[1].init.body), { snippet: { parentId: "Ug1", textOriginal: "thanks" } });
});

test("youtube: analytics_post reads statistics, delete answers 204 (wire)", async () => {
  const client = await connect(SPEC, (url, init) => url.href === TOKEN ? tok : init.method === "DELETE" ? { status: 204, raw: "" } : { body: { items: [{ id: "vid1", statistics: { viewCount: "10" } }] } });
  const res = await client.callTool({ name: "analytics_post", arguments: { post_id: "vid1" } });
  assert.deepEqual(res.structuredContent.metrics, { viewCount: "10" });
  const del = await client.callTool({ name: "delete", arguments: { post_id: "vid1" } });
  assert.equal(del.structuredContent.status, "deleted");
});
