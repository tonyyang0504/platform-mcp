import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/messaging/telegram.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { token: "123:ABC" }, 50, "test", fakeFetch(handler), SPEC.adapter.envelope));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("telegram: tools follow the messaging vocabulary (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["list_inbound", "me", "send"]);
  const send = tools.find((t) => t.name === "send");
  assert.equal(send.annotations.readOnlyHint, false);
  assert.deepEqual(send.inputSchema.required, ["to", "text"]);
  assert.equal(send._meta["platform_mcp/endpoint"], "/sendMessage");
});

test("telegram: send puts the token in the URL path, not in a header (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { ok: true, result: { message_id: 42, date: 1700000000, chat: { id: 987, type: "private" }, text: "hello" } } }; });
  const res = await client.callTool({ name: "send", arguments: { to: "987", text: "hello" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.message_id, "42");
  assert.equal(seen.url.href, "https://api.telegram.org/bot123:ABC/sendMessage");
  assert.deepEqual(JSON.parse(seen.init.body), { chat_id: "987", text: "hello" });
  assert.equal(seen.init.headers.Authorization, undefined);
});

test("telegram: list_inbound polls getUpdates without an offset (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { ok: true, result: [{ update_id: 1001, message: { message_id: 5, chat: { id: 987 }, text: "hi bot" } }] } }; });
  const res = await client.callTool({ name: "list_inbound", arguments: { limit: 10 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.messages[0].id, "1001");
  assert.equal(res.structuredContent.messages[0].text, "hi bot");
  assert.equal(seen.href, "https://api.telegram.org/bot123:ABC/getUpdates?limit=10");
});

test("telegram: ok:false envelope is an isError result (wire)", async () => {
  const client = await connect(() => ({ body: { ok: false, error_code: 401, description: "Unauthorized" } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
});
