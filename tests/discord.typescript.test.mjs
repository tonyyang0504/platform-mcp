import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/messaging/discord.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { bot_token: "bot-secret-token" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("discord: tools follow the messaging vocabulary (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_thread", "list_inbound", "me", "reply", "send"]);
  const send = tools.find((t) => t.name === "send");
  assert.equal(send.annotations.readOnlyHint, false);
  assert.equal(send.annotations.destructiveHint, false);
  assert.equal(send.title, "Send a message");
  assert.deepEqual(send.inputSchema.required, ["to", "text"]);
  assert.equal(send._meta["platform_mcp/endpoint"], "/channels/{to}/messages");
  assert.deepEqual(Object.keys(SPEC.adapter.not_offered), ["mark_read"]);
});

test("discord: reply posts a message_reference with the 'Bot ' prefixed token (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { id: "334385199974967042", channel_id: "1001", author: { id: "80351110224678912", username: "Nelly" }, content: "hi", timestamp: "2017-07-11T17:27:07.299000+00:00" } }; });
  const res = await client.callTool({ name: "reply", arguments: { thread_id: "306588351130107906", channel: "1001", text: "hi" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.message_id, "334385199974967042");
  assert.equal(res.structuredContent.status, "sent");
  assert.equal(seen.url.href, "https://discord.com/api/v10/channels/1001/messages");
  assert.equal(seen.init.method, "POST");
  assert.deepEqual(JSON.parse(seen.init.body), { content: "hi", message_reference: { message_id: "306588351130107906" } });
  assert.equal(seen.init.headers.Authorization, "Bot bot-secret-token");
});

test("discord: list_inbound lists one channel, newest first (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: [{ id: "334385199974967042", channel_id: "1001", author: { id: "80351110224678912", username: "Nelly" }, content: "Supa dupa", timestamp: "2017-07-11T17:27:07.299000+00:00" }] }; });
  const res = await client.callTool({ name: "list_inbound", arguments: { channel: "1001", limit: 10 } });
  assert.equal(res.isError, false);
  const m = res.structuredContent.messages[0];
  assert.equal(m.id, "334385199974967042");
  assert.equal(m.from, "80351110224678912");
  assert.equal(m.text, "Supa dupa");
  assert.equal(m.thread_id, "1001");
  assert.equal(m.sent_at, "2017-07-11T17:27:07.299000+00:00");
  assert.equal(res.structuredContent.next_page, null);
  assert.equal(seen.pathname, "/api/v10/channels/1001/messages");
  assert.equal(seen.searchParams.get("limit"), "10");
});

test("discord: 401 is an auth_error result that does not leak the token (wire)", async () => {
  const client = await connect(() => ({ status: 401, body: { message: "401: Unauthorized", code: 0 } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.equal(res.structuredContent.http_status, 401);
  assert.ok(!JSON.stringify(res.structuredContent).includes("bot-secret-token"));
});
