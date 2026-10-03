import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/reddit.json", import.meta.url), "utf8"));
const UA = "server:com.example.app:v1.0 (by /u/example)";
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

process.env.PLATFORM_MCP_REDDIT_CLIENT_ID = "cid";
process.env.PLATFORM_MCP_REDDIT_CLIENT_SECRET = "csec";
process.env.PLATFORM_MCP_REDDIT_USER_AGENT = UA;

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("reddit read_comments exchanges client credentials then reads the second listing (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => {
    seen.push({ url, init });
    if (url.href === "https://www.reddit.com/api/v1/access_token") return { body: { access_token: "AT1", token_type: "bearer", expires_in: 3600, scope: "*" } };
    return { body: [
      { kind: "Listing", data: { children: [{ kind: "t3", data: { id: "1abc23", name: "t3_1abc23" } }] } },
      { kind: "Listing", data: { children: [{ kind: "t1", data: { id: "k9x1", name: "t1_k9x1", author: "someone", body: "first!", created_utc: 1758708000 } }] } },
    ] };
  });
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["analytics_post", "read_comments"]);
  const res = await client.callTool({ name: "read_comments", arguments: { post_id: "1abc23" } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].init.method, "POST");
  assert.equal(seen[0].init.headers.Authorization, "Basic " + Buffer.from("cid:csec").toString("base64"));
  assert.match(seen[0].init.body, /grant_type=client_credentials/);
  assert.equal(seen[1].url.href, "https://oauth.reddit.com/comments/1abc23?limit=25");
  assert.equal(seen[1].init.headers.Authorization, "Bearer AT1");
  assert.ok(seen[1].init.headers["User-Agent"].endsWith(UA));
  const c = res.structuredContent.comments[0];
  assert.equal(c.id, "k9x1"); assert.equal(c.author, "someone"); assert.equal(c.text, "first!");
});

test("reddit rejected client secret is an auth_error result (wire)", async () => {
  const client = await connect(() => ({ status: 401, body: { error: 401, message: "Unauthorized" } }));
  const res = await client.callTool({ name: "analytics_post", arguments: { post_id: "t3_1abc23" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
});
