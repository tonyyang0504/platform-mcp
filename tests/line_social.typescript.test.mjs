import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/line.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { channel_access_token: "line-social-secret" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("line social: publish_text broadcasts a text message (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: {} }; });
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["analytics_post", "me", "publish_image", "publish_text"]);
  const res = await client.callTool({ name: "publish_text", arguments: { text: "hi" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "broadcast");
  assert.equal(seen.url.href, "https://api.line.me/v2/bot/message/broadcast");
  assert.deepEqual(JSON.parse(seen.init.body), { messages: [{ type: "text", text: "hi" }] });
  assert.equal(seen.init.headers.Authorization, "Bearer line-social-secret");
});

test("line social: analytics_post maps the overview (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { overview: { requestId: "r1", delivered: 320, uniqueImpression: 82, uniqueClick: 51 } } }; });
  const res = await client.callTool({ name: "analytics_post", arguments: { post_id: "r1" } });
  assert.equal(res.isError, false);
  assert.equal(seen.searchParams.get("requestId"), "r1");
  assert.equal(res.structuredContent.post_id, "r1");
  assert.equal(res.structuredContent.unique_impression, 82);
});
