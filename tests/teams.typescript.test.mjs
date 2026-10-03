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
const SPEC = JSON.parse(readFileSync(new URL("../catalog/messaging/teams.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_TEAMS_CLIENT_ID: "app", PLATFORM_MCP_TEAMS_REFRESH_TOKEN: "0.AR", PLATFORM_MCP_TEAMS_TEAM_ID: "T1", PLATFORM_MCP_TEAMS_USER_ID: "U1", PLATFORM_MCP_TEAMS_TENANT_ID: "TN" });
const TOKEN = "https://login.microsoftonline.com/common/oauth2/v2.0/token";
const tok = { body: { access_token: "eyJ.T", expires_in: 3600 } };

test("teams: tools (wire)", async () => {
  assert.deepEqual(await names(SPEC), ["get_thread", "list_inbound", "mark_read", "me", "reply", "send"]);
});

test("teams: send to a chat and reply in a channel thread (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { if (url.href === TOKEN) return tok; seen.push({ url, init }); return { status: 201, body: { id: "42" } }; });
  const s = await client.callTool({ name: "send", arguments: { to: "19:abc@thread.v2", text: "hi" } });
  assert.equal(s.structuredContent.message_id, "42");
  assert.equal(decodeURIComponent(seen[0].url.pathname), "/v1.0/chats/19:abc@thread.v2/messages");
  await client.callTool({ name: "reply", arguments: { thread_id: "111", channel: "19:ch@thread.tacv2", text: "ok" } });
  assert.equal(decodeURIComponent(seen[1].url.pathname), "/v1.0/teams/T1/channels/19:ch@thread.tacv2/messages/111/replies");
  assert.deepEqual(JSON.parse(seen[1].init.body), { body: { content: "ok" } });
});

test("teams: mark_read sends the configured user identity (wire)", async () => {
  let last;
  const client = await connect(SPEC, (url, init) => { if (url.href === TOKEN) return tok; last = { url, init }; return { status: 204, raw: "" }; });
  const res = await client.callTool({ name: "mark_read", arguments: { channel: "19:abc@thread.v2" } });
  assert.equal(res.structuredContent.status, "read");
  assert.deepEqual(JSON.parse(last.init.body), { user: { id: "U1", tenantId: "TN" } });
});
