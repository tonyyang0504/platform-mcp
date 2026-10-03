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
const SPEC = JSON.parse(readFileSync(new URL("../catalog/messaging/google_chat.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_GOOGLE_CHAT_CLIENT_ID: "cid", PLATFORM_MCP_GOOGLE_CHAT_CLIENT_SECRET: "s", PLATFORM_MCP_GOOGLE_CHAT_REFRESH_TOKEN: "r" });
const TOKEN = "https://oauth2.googleapis.com/token";
const tok = { body: { access_token: "ya29.C", expires_in: 3599 } };

test("google_chat: tools (wire)", async () => {
  assert.deepEqual(await names(SPEC), ["get_thread", "list_inbound", "mark_read", "me", "reply", "send"]);
});

test("google_chat: reply in a thread (wire)", async () => {
  let last;
  const client = await connect(SPEC, (url, init) => { if (url.href === TOKEN) return tok; last = { url, init }; return { body: { name: "spaces/AAA/messages/m2" } }; });
  const res = await client.callTool({ name: "reply", arguments: { thread_id: "spaces/AAA/threads/t1", channel: "AAA", text: "ok" } });
  assert.equal(res.structuredContent.message_id, "spaces/AAA/messages/m2");
  assert.equal(last.url.pathname, "/v1/spaces/AAA/messages");
  assert.equal(last.url.searchParams.get("messageReplyOption"), "REPLY_MESSAGE_FALLBACK_TO_NEW_THREAD");
  assert.deepEqual(JSON.parse(last.init.body), { text: "ok", thread: { name: "spaces/AAA/threads/t1" } });
});

test("google_chat: get_thread filter and mark_read (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { if (url.href === TOKEN) return tok; seen.push({ url, init }); return { body: { messages: [{ name: "spaces/AAA/messages/m1", text: "hi", sender: { name: "users/1" } }] } }; });
  const res = await client.callTool({ name: "get_thread", arguments: { thread_id: "spaces/AAA/threads/t1", channel: "AAA" } });
  assert.equal(res.structuredContent.messages[0].from, "users/1");
  assert.equal(seen[0].url.searchParams.get("filter"), "thread.name = spaces/AAA/threads/t1");
  await client.callTool({ name: "mark_read", arguments: { channel: "AAA" } });
  assert.equal(seen[1].init.method, "PATCH");
  assert.equal(seen[1].url.pathname, "/v1/users/me/spaces/AAA/spaceReadState");
  assert.equal(seen[1].url.searchParams.get("updateMask"), "lastReadTime");
});
