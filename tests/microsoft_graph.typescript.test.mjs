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
const SPEC = JSON.parse(readFileSync(new URL("../catalog/messaging/microsoft_graph.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_MICROSOFT_GRAPH_CLIENT_ID: "app", PLATFORM_MCP_MICROSOFT_GRAPH_REFRESH_TOKEN: "0.AR" });
const TOKEN = "https://login.microsoftonline.com/common/oauth2/v2.0/token";
const tok = { body: { access_token: "eyJ.M", expires_in: 3600 } };

test("microsoft_graph: tools (wire)", async () => {
  assert.deepEqual(await names(SPEC), ["get_thread", "list_inbound", "mark_read", "me", "reply", "send"]);
});

test("microsoft_graph: sendMail JSON body, 202 without body (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return url.href === TOKEN ? tok : { status: 202, raw: "" }; });
  const res = await client.callTool({ name: "send", arguments: { to: "fran@contoso.com", text: "Lunch?", subject: "Hi" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "sent");
  assert.equal(form(seen[0].init.body).client_id, "app");
  assert.equal(form(seen[0].init.body).client_secret, undefined);
  assert.deepEqual(JSON.parse(seen[1].init.body), { message: { subject: "Hi", body: { contentType: "Text", content: "Lunch?" }, toRecipients: [{ emailAddress: { address: "fran@contoso.com" } }] } });
});

test("microsoft_graph: inbox with literal $top, mark_read PATCH (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { if (url.href === TOKEN) return tok; seen.push({ url, init }); return { body: { value: [{ id: "AAMk1", conversationId: "c1", bodyPreview: "hey", from: { emailAddress: { address: "a@b.c" } } }] } }; });
  const res = await client.callTool({ name: "list_inbound", arguments: { limit: 5 } });
  assert.equal(res.structuredContent.messages[0].from, "a@b.c");
  assert.match(seen[0].url.href, /\$top=5/);
  await client.callTool({ name: "mark_read", arguments: { message_id: "AAMk1" } });
  assert.equal(seen[1].init.method, "PATCH");
  assert.deepEqual(JSON.parse(seen[1].init.body), { isRead: true });
});
