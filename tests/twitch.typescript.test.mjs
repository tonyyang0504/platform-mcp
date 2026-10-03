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
const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/twitch.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_TWITCH_CLIENT_ID: "wbmy", PLATFORM_MCP_TWITCH_CLIENT_SECRET: "sec", PLATFORM_MCP_TWITCH_REFRESH_TOKEN: "eyJr", PLATFORM_MCP_TWITCH_BROADCASTER_ID: "12826", PLATFORM_MCP_TWITCH_SENDER_ID: "141981764" });
const TOKEN = "https://id.twitch.tv/oauth2/token";
const tok = { body: { access_token: "2gbd", expires_in: 15583 } };

test("twitch: tools (wire)", async () => {
  assert.deepEqual(await names(SPEC), ["delete", "me", "publish_text", "reply_comment"]);
});

test("twitch: publish_text sends Client-Id and the configured ids (wire)", async () => {
  let last;
  const client = await connect(SPEC, (url, init) => { if (url.href === TOKEN) return tok; last = { url, init }; return { body: { data: [{ message_id: "abc-123", is_sent: true }] } }; });
  const res = await client.callTool({ name: "publish_text", arguments: { text: "Hello chat" } });
  assert.equal(res.structuredContent.id, "abc-123");
  assert.equal(last.init.headers["Client-Id"], "wbmy");
  assert.deepEqual(JSON.parse(last.init.body), { broadcaster_id: "12826", sender_id: "141981764", message: "Hello chat" });
});

test("twitch: delete always names one message (wire)", async () => {
  let last;
  const client = await connect(SPEC, (url, init) => { if (url.href === TOKEN) return tok; last = url; return { status: 204, raw: "" }; });
  const res = await client.callTool({ name: "delete", arguments: { post_id: "abc-123" } });
  assert.equal(res.structuredContent.status, "deleted");
  assert.equal(last.searchParams.get("message_id"), "abc-123");
  assert.equal(last.searchParams.get("moderator_id"), "141981764");
  const bad = await client.callTool({ name: "delete", arguments: { post_id: "" } });
  assert.equal(bad.isError, true);
});
