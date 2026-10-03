import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/discord.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (r.status === 204 ? "" : JSON.stringify(r.body ?? {})) }; };

// channel_id is a config field: with an injected transport the adapter resolves `@channel_id` from transport.creds
async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { bot_token: "bot-secret-token", channel_id: "1001" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("discord (social) publish_text posts into the configured channel with the Bot-prefixed token (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { id: "334385199974967042", channel_id: "1001", author: { id: "9", username: "Nelly" }, content: "hello", timestamp: "2026-09-24T00:00:00+00:00" } }; });
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["delete", "me", "publish_image", "publish_text", "read_comments", "reply_comment"]);
  const res = await client.callTool({ name: "publish_text", arguments: { text: "hello", reply_to: "306588351130107906" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "334385199974967042");
  assert.equal(seen.url.href, "https://discord.com/api/v10/channels/1001/messages");
  assert.deepEqual(JSON.parse(seen.init.body), { content: "hello", message_reference: { message_id: "306588351130107906" } });
  assert.equal(seen.init.headers.Authorization, "Bot bot-secret-token");
  const img = await client.callTool({ name: "publish_image", arguments: { text: "pics", image_urls: ["https://img.example/a.png", "https://img.example/b.png"] } });
  assert.equal(img.isError, false);
  assert.deepEqual(JSON.parse(seen.init.body), { content: "pics", embeds: [{ image: { url: "https://img.example/a.png" } }, { image: { url: "https://img.example/b.png" } }] });
});

test("discord (social) read_comments lists the thread named by post_id and delete answers a literal status (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => {
    seen.push({ url, init });
    if (init.method === "DELETE") return { status: 204 };
    return { body: [{ id: "2", channel_id: "5555", author: { id: "9", username: "zsc" }, content: "second", timestamp: "2026-09-24T10:05:00+00:00" }] };
  });
  const res = await client.callTool({ name: "read_comments", arguments: { post_id: "5555", limit: 10 } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].url.href, "https://discord.com/api/v10/channels/5555/messages?limit=10");
  assert.equal(res.structuredContent.comments[0].author, "zsc");
  assert.equal(res.structuredContent.next_page, null);
  const del = await client.callTool({ name: "delete", arguments: { post_id: "42" } });
  assert.equal(del.isError, false);
  assert.equal(del.structuredContent.status, "deleted");
  assert.equal(seen[1].url.href, "https://discord.com/api/v10/channels/1001/messages/42");
  assert.equal(seen[1].init.method, "DELETE");
});
