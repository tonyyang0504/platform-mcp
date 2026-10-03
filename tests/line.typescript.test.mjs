import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/messaging/line.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { channel_access_token: "line-secret-token" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("line: tools follow the messaging vocabulary (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["me", "send"]);
  const send = tools.find((t) => t.name === "send");
  assert.equal(send.annotations.readOnlyHint, false);
  assert.deepEqual(send.inputSchema.required, ["to", "text"]);
  assert.equal(send._meta["platform_mcp/endpoint"], "/v2/bot/message/push");
  assert.deepEqual(Object.keys(SPEC.adapter.not_offered).sort(), ["get_thread", "list_inbound", "mark_read", "reply"]);
});

test("line: send pushes one text message object with the channel access token (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { sentMessages: [{ id: "461230966842064897", quoteToken: "IStG5h1Qz-..." }] } }; });
  const res = await client.callTool({ name: "send", arguments: { to: "U4af4980629...", text: "Hello, world", subject: "ignored" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.message_id, "461230966842064897");
  assert.equal(res.structuredContent.status, "sent");
  assert.equal(seen.url.href, "https://api.line.me/v2/bot/message/push");
  assert.deepEqual(JSON.parse(seen.init.body), { to: "U4af4980629...", messages: [{ type: "text", text: "Hello, world" }] });
  assert.equal(seen.init.headers.Authorization, "Bearer line-secret-token");
});

test("line: me reads the bot info (wire)", async () => {
  const client = await connect(() => ({ body: { userId: "Ub9952f8...", basicId: "@216ru...", displayName: "Example name", chatMode: "chat", markAsReadMode: "manual" } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.ok, true);
  assert.equal(res.structuredContent.account.basicId, "@216ru...");
});

test("line: 401 is an auth_error result that does not leak the token (wire)", async () => {
  const client = await connect(() => ({ status: 401, body: { message: "Authentication failed. Confirm that the access token in the authorization header is valid." } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.ok(!JSON.stringify(res.structuredContent).includes("line-secret-token"));
});
