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
const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/google_business.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_GOOGLE_BUSINESS_CLIENT_ID: "cid", PLATFORM_MCP_GOOGLE_BUSINESS_CLIENT_SECRET: "s", PLATFORM_MCP_GOOGLE_BUSINESS_REFRESH_TOKEN: "r", PLATFORM_MCP_GOOGLE_BUSINESS_ACCOUNT_ID: "111", PLATFORM_MCP_GOOGLE_BUSINESS_LOCATION_ID: "222" });
const TOKEN = "https://oauth2.googleapis.com/token";
const tok = { body: { access_token: "ya29.B", expires_in: 3599 } };

test("google_business: tools (wire)", async () => {
  assert.deepEqual(await names(SPEC), ["delete", "me", "publish_image", "publish_text", "read_mentions", "reply_comment"]);
});

test("google_business: publish_text posts a STANDARD local post under the configured location (wire)", async () => {
  let last;
  const client = await connect(SPEC, (url, init) => { if (url.href === TOKEN) return tok; last = { url, init }; return { body: { name: "accounts/111/locations/222/localPosts/9", createTime: "2026-09-24T00:00:00Z" } }; });
  const res = await client.callTool({ name: "publish_text", arguments: { text: "Open late" } });
  assert.equal(res.structuredContent.id, "accounts/111/locations/222/localPosts/9");
  assert.equal(last.url.pathname, "/v4/accounts/111/locations/222/localPosts");
  assert.deepEqual(JSON.parse(last.init.body), { summary: "Open late", topicType: "STANDARD" });
});

test("google_business: reviews as mentions, reply via PUT (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { if (url.href === TOKEN) return tok; seen.push({ url, init }); return init.method === "PUT" ? { body: { comment: "thanks", updateTime: "t" } } : { body: { reviews: [{ reviewId: "r1", reviewer: { displayName: "Bo" }, comment: "great" }] } }; });
  const r = await client.callTool({ name: "read_mentions", arguments: {} });
  assert.equal(r.structuredContent.mentions[0].author, "Bo");
  await client.callTool({ name: "reply_comment", arguments: { comment_id: "r1", text: "thanks" } });
  assert.equal(seen[1].url.pathname, "/v4/accounts/111/locations/222/reviews/r1/reply");
  assert.deepEqual(JSON.parse(seen[1].init.body), { comment: "thanks" });
});
