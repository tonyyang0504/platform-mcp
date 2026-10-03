import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/messaging/messenger.json", import.meta.url), "utf8"));
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

process.env.PLATFORM_MCP_MESSENGER_PAGE_ACCESS_TOKEN = "PAGE-TOKEN";
process.env.PLATFORM_MCP_MESSENGER_PAGE_ID = "1234";

test("messenger send uses the Send API body (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { recipient_id: "PSID1", message_id: "m_1" } }; });
  const res = await client.callTool({ name: "send", arguments: { to: "PSID1", text: "Hello" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.message_id, "m_1");
  assert.equal(seen.url.href, "https://graph.facebook.com/v26.0/1234/messages");
  assert.deepEqual(JSON.parse(seen.init.body), { recipient: { id: "PSID1" }, messaging_type: "RESPONSE", message: { text: "Hello" } });
});

test("messenger list_inbound maps the latest message per conversation (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { data: [{ id: "t_1", messages: { data: [{ id: "m_1", message: "hi", from: { name: "Ann", id: "PSID1" }, created_time: "2026-09-24T10:00:00+0000" }] } }] } }; });
  const res = await client.callTool({ name: "list_inbound", arguments: {} });
  assert.equal(res.isError, false);
  assert.equal(seen.searchParams.get("platform"), "messenger");
  assert.equal(res.structuredContent.messages[0].thread_id, "t_1");
  assert.equal(res.structuredContent.messages[0].from_id, "PSID1");
});
