import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/messaging/slack.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { token: "xoxb-test" }, 50, "test", fakeFetch(handler), SPEC.adapter.envelope));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("slack: tools follow the messaging vocabulary (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_thread", "list_inbound", "mark_read", "me", "reply", "send"]);
  const send = tools.find((t) => t.name === "send");
  assert.equal(send.annotations.readOnlyHint, false);
  assert.equal(send.annotations.destructiveHint, false);
  assert.equal(send.title, "Send a message");
  assert.deepEqual(send.inputSchema.required, ["to", "text"]);
  assert.equal(send._meta["platform_mcp/endpoint"], "/chat.postMessage");
});

test("slack: reply posts thread_ts + channel with a bearer token (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { ok: true, channel: "C123", ts: "1503435956.000247", message: { type: "message", text: "hi" } } }; });
  const res = await client.callTool({ name: "reply", arguments: { thread_id: "1503435900.000100", channel: "C123", text: "hi" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.message_id, "1503435956.000247");
  assert.equal(seen.url.href, "https://slack.com/api/chat.postMessage");
  assert.deepEqual(JSON.parse(seen.init.body), { channel: "C123", thread_ts: "1503435900.000100", text: "hi" });
  assert.equal(seen.init.headers.Authorization, "Bearer xoxb-test");
});

test("slack: list_inbound lists one channel (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { ok: true, messages: [{ type: "message", user: "U012AB3CDE", text: "I find you punny", ts: "1512085950.000216" }], has_more: false } }; });
  const res = await client.callTool({ name: "list_inbound", arguments: { channel: "C123", limit: 10 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.messages[0].id, "1512085950.000216");
  assert.equal(res.structuredContent.messages[0].from, "U012AB3CDE");
  assert.equal(seen.searchParams.get("channel"), "C123");
  assert.equal(seen.searchParams.get("limit"), "10");
});

test("slack: ok:false envelope is an isError result (wire)", async () => {
  const client = await connect(() => ({ body: { ok: false, error: "invalid_auth" } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
});
