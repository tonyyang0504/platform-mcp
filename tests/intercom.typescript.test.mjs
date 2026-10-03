import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/messaging/intercom.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  // admin_id is a non-secret per-install config field (the authoring admin for replies / messages)
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { access_token: "dG9rZW4-secret", admin_id: "991267386" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("intercom: tools follow the messaging vocabulary (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_thread", "list_inbound", "mark_read", "me", "reply", "send"]);
  const reply = tools.find((t) => t.name === "reply");
  assert.equal(reply.annotations.readOnlyHint, false);
  assert.equal(reply.annotations.destructiveHint, false);
  assert.deepEqual(reply.inputSchema.required, ["thread_id", "text"]);
  assert.equal(reply._meta["platform_mcp/endpoint"], "/conversations/{thread_id}/reply");
  assert.deepEqual(SPEC.adapter.not_offered, {});
});

test("intercom: send creates an admin in-app message with a bearer token (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { type: "admin_message", id: "403918396", created_at: 1734537780, body: "heyy", message_type: "inapp", conversation_id: "613" } }; });
  const res = await client.callTool({ name: "send", arguments: { to: "6762f2341bb69f9f2193bc17", text: "heyy", subject: "ignored" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.message_id, "403918396");
  assert.equal(res.structuredContent.status, "sent");
  assert.equal(seen.url.href, "https://api.intercom.io/messages");
  assert.deepEqual(JSON.parse(seen.init.body), { message_type: "in_app", body: "heyy", from: { type: "admin", id: "991267386" }, to: { type: "user", id: "6762f2341bb69f9f2193bc17" } });
  assert.equal(seen.init.headers.Authorization, "Bearer dG9rZW4-secret");
});

test("intercom: reply posts an admin comment on the conversation (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { type: "conversation", id: "123", state: "open", conversation_parts: { type: "conversation_part.list", conversation_parts: [{ id: "3", part_type: "comment", body: "Thanks" }], total_count: 1 } } }; });
  const res = await client.callTool({ name: "reply", arguments: { thread_id: "123", text: "Thanks" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "sent");
  assert.equal(seen.url.href, "https://api.intercom.io/conversations/123/reply");
  assert.deepEqual(JSON.parse(seen.init.body), { message_type: "comment", type: "admin", admin_id: "991267386", body: "Thanks" });
});

test("intercom: list_inbound maps conversations and get_thread maps parts (wire)", async () => {
  let seen;
  const client = await connect((url) => {
    seen = url;
    if (url.pathname === "/conversations") return { body: { type: "conversation.list", total_count: 1, conversations: [{ type: "conversation", id: "471", created_at: 1734537460, source: { id: "403918320", body: "<p>this is the message body</p>", author: { type: "user", id: "6762", email: "joe@example.com" } } }] } };
    return { body: { type: "conversation", id: "471", conversation_parts: { total_count: 1, conversation_parts: [{ type: "conversation_part", id: "3", part_type: "comment", body: "Okay!", created_at: 1663597223, author: { type: "admin", id: "991267386", email: "admin@example.com" } }] } } };
  });
  let res = await client.callTool({ name: "list_inbound", arguments: { limit: 10 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.messages[0].id, "471");
  assert.equal(res.structuredContent.messages[0].thread_id, "471");
  assert.equal(res.structuredContent.messages[0].from, "joe@example.com");
  assert.equal(seen.searchParams.get("per_page"), "10");
  res = await client.callTool({ name: "get_thread", arguments: { thread_id: "471" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.messages[0].id, "3");
  assert.equal(res.structuredContent.messages[0].text, "Okay!");
  assert.equal(res.structuredContent.total, 1);
  assert.equal(seen.pathname, "/conversations/471");
  assert.equal(seen.searchParams.get("display_as"), "plaintext");
});

test("intercom: 401 is an auth_error result that does not leak the token (wire)", async () => {
  const client = await connect(() => ({ status: 401, body: { type: "error.list", errors: [{ code: "token_unauthorized", message: "Access Token Invalid" }] } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.ok(!JSON.stringify(res.structuredContent).includes("dG9rZW4-secret"));
});

test("intercom: mark_read puts a JSON boolean (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { type: "conversation", id: "471", read: true } }; });
  const res = await client.callTool({ name: "mark_read", arguments: { thread_id: "471" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "read");
  assert.equal(seen.init.method, "PUT");
  assert.equal(seen.url.href, "https://api.intercom.io/conversations/471");
  assert.deepEqual(JSON.parse(seen.init.body), { read: true });
});
