import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/messaging/crisp.json", import.meta.url), "utf8"));
const BASE = "https://api.crisp.chat/v1/website/8c842203-7ed8-4e29-a608-7cf78a7d2fcc";
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  // identifier:key go into HTTP Basic; X-Crisp-Tier is a static adapter header; website_id a config field
  const creds = { identifier: "crisp-identifier", key: "crisp-secret-key", website_id: "8c842203-7ed8-4e29-a608-7cf78a7d2fcc" };
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("crisp: tools follow the messaging vocabulary (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_thread", "list_inbound", "mark_read", "me", "reply"]);
  const reply = tools.find((t) => t.name === "reply");
  assert.equal(reply.annotations.readOnlyHint, false);
  assert.equal(reply.annotations.destructiveHint, false);
  assert.deepEqual(reply.inputSchema.required, ["thread_id", "text"]);
  assert.equal(reply._meta["platform_mcp/endpoint"], "/website/{website_id}/conversation/{thread_id}/message");
  assert.deepEqual(Object.keys(SPEC.adapter.not_offered), ["send"]);
});

test("crisp: reply sends an operator text message with Basic auth and the tier header (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { error: false, reason: "dispatched", data: { fingerprint: 163613151617340 } } }; });
  const res = await client.callTool({ name: "reply", arguments: { thread_id: "session_19e5240f", text: "Hello there" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.message_id, "163613151617340");
  assert.equal(res.structuredContent.status, "dispatched");
  assert.equal(seen.url.href, `${BASE}/conversation/session_19e5240f/message`);
  assert.equal(seen.init.method, "POST");
  assert.deepEqual(JSON.parse(seen.init.body), { type: "text", from: "operator", origin: "chat", content: "Hello there" });
  assert.equal(seen.init.headers.Authorization, "Basic " + Buffer.from("crisp-identifier:crisp-secret-key").toString("base64"));
  assert.equal(seen.init.headers["X-Crisp-Tier"], "plugin");
});

test("crisp: list_inbound pages by path segment and maps conversations (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { error: false, reason: "listed", data: [{ session_id: "session_19e5240f", state: "unresolved", last_message: "Hey there!", updated_at: 1544451612345, meta: { nickname: "Valerian", email: "valerian@crisp.chat" } }] } }; });
  const res = await client.callTool({ name: "list_inbound", arguments: { page: 2, limit: 30, since: "2018-03-01T17:00:00.000Z" } });
  assert.equal(res.isError, false);
  const m = res.structuredContent.messages[0];
  assert.equal(m.id, "session_19e5240f");
  assert.equal(m.thread_id, "session_19e5240f");
  assert.equal(m.from, "valerian@crisp.chat");
  assert.equal(m.text, "Hey there!");
  assert.equal(seen.pathname, "/v1/website/8c842203-7ed8-4e29-a608-7cf78a7d2fcc/conversations/2");
  assert.equal(seen.searchParams.get("per_page"), "30");
  assert.equal(seen.searchParams.get("filter_date_start"), "2018-03-01T17:00:00.000Z");
});

test("crisp: mark_read patches all visitor messages of the conversation (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { error: false, reason: "updated", data: {} } }; });
  const res = await client.callTool({ name: "mark_read", arguments: { thread_id: "session_19e5240f" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "updated");
  assert.equal(seen.init.method, "PATCH");
  assert.equal(seen.url.href, `${BASE}/conversation/session_19e5240f/read`);
  assert.deepEqual(JSON.parse(seen.init.body), { from: "user", origin: "chat" });
});

test("crisp: 401 is an auth_error result that does not leak the credential (wire)", async () => {
  const client = await connect(() => ({ status: 401, body: { error: true, reason: "invalid_session", data: {} } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.ok(!JSON.stringify(res.structuredContent).includes("crisp-secret-key"));
});
