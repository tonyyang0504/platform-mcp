import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/x.json", import.meta.url), "utf8"));
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

const TOKEN_URL = "https://api.x.com/2/oauth2/token";
const tokenOk = { body: { token_type: "bearer", expires_in: 7200, access_token: "ACCESS1", refresh_token: "REFRESH2" } };
process.env.PLATFORM_MCP_X_CLIENT_ID = "CLIENTID";
process.env.PLATFORM_MCP_X_CLIENT_SECRET = "CLIENTSECRET";
process.env.PLATFORM_MCP_X_REFRESH_TOKEN = "REFRESHsecret";
process.env.PLATFORM_MCP_X_USER_ID = "2244994945";

test("x: refresh grant with HTTP Basic, bearer on POST /2/tweets (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => { seen.push({ url, init }); return url.href === TOKEN_URL ? tokenOk : { status: 201, body: { data: { id: "1445880548472328192", text: "hi" } } }; });
  const res = await client.callTool({ name: "publish_text", arguments: { text: "hi", reply_to: "1445880548472328100" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "1445880548472328192");
  const tok = seen.find((s) => s.url.href === TOKEN_URL);
  assert.deepEqual(Object.fromEntries(new URLSearchParams(tok.init.body)), { grant_type: "refresh_token", refresh_token: "REFRESHsecret" });
  assert.equal(tok.init.headers.Authorization, "Basic " + Buffer.from("CLIENTID:CLIENTSECRET").toString("base64"));
  const call = seen.find((s) => s.url.href === "https://api.x.com/2/tweets");
  assert.deepEqual(JSON.parse(call.init.body), { text: "hi", reply: { in_reply_to_tweet_id: "1445880548472328100" } });
  assert.equal(call.init.headers.Authorization, "Bearer ACCESS1");
});

test("x: analytics_post returns public_metrics as metrics (wire)", async () => {
  let seen;
  const client = await connect((url) => { if (url.href === TOKEN_URL) return tokenOk; seen = url; return { body: { data: { id: "1", public_metrics: { like_count: 3, reply_count: 2, repost_count: 1, quote_count: 0, bookmark_count: 0, impression_count: 50 } } } }; });
  const res = await client.callTool({ name: "analytics_post", arguments: { post_id: "1" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.metrics.like_count, 3);
  assert.equal(seen.searchParams.get("post.fields"), "public_metrics,created_at");
});
