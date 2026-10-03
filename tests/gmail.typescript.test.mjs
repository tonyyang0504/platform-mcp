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
const SPEC = JSON.parse(readFileSync(new URL("../catalog/messaging/gmail.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_GMAIL_CLIENT_ID: "cid", PLATFORM_MCP_GMAIL_CLIENT_SECRET: "gsec", PLATFORM_MCP_GMAIL_REFRESH_TOKEN: "1//r" });
const TOKEN = "https://oauth2.googleapis.com/token";

test("gmail: tools (wire)", async () => {
  assert.deepEqual(await names(SPEC), ["get_thread", "list_inbound", "mark_read", "me"]);
});

test("gmail: refresh grant in the body, then list inbox ids (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return url.href === TOKEN ? { body: { access_token: "ya29.A", expires_in: 3599 } } : { body: { messages: [{ id: "m1", threadId: "t1" }], resultSizeEstimate: 1 } }; });
  const res = await client.callTool({ name: "list_inbound", arguments: { limit: 10 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.messages[0].thread_id, "t1");
  const f = form(seen[0].init.body);
  assert.equal(f.grant_type, "refresh_token"); assert.equal(f.client_secret, "gsec"); assert.equal(f.client_id, "cid");
  assert.equal(seen[1].url.searchParams.get("labelIds"), "INBOX");
  assert.equal(seen[1].init.headers.Authorization, "Bearer ya29.A");
});

test("gmail: mark_read removes the UNREAD label (wire)", async () => {
  let last;
  const client = await connect(SPEC, (url, init) => { if (url.href === TOKEN) return { body: { access_token: "ya29.A", expires_in: 3599 } }; last = { url, init }; return { body: { id: "m1" } }; });
  const res = await client.callTool({ name: "mark_read", arguments: { message_id: "m1" } });
  assert.equal(res.structuredContent.status, "read");
  assert.equal(last.url.pathname, "/gmail/v1/users/me/messages/m1/modify");
  assert.deepEqual(JSON.parse(last.init.body), { removeLabelIds: ["UNREAD"] });
});
