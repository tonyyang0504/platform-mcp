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
const SPEC = JSON.parse(readFileSync(new URL("../catalog/messaging/zendesk.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_ZENDESK_EMAIL_TOKEN: "jdoe@example.com/token", PLATFORM_MCP_ZENDESK_API_TOKEN: "6wiIBWbG", PLATFORM_MCP_ZENDESK_SUBDOMAIN: "acme" });

test("zendesk: tools (wire)", async () => {
  assert.deepEqual(await names(SPEC), ["get_thread", "list_inbound", "me", "reply", "send"]);
});

test("zendesk: basic email/token auth on the subdomain, tickets list (wire)", async () => {
  let last;
  const client = await connect(SPEC, (url, init) => { last = { url, init }; return { body: { tickets: [{ id: 35436, description: "fire", requester_id: 7 }], count: 1 } }; });
  const res = await client.callTool({ name: "list_inbound", arguments: { page: 2, limit: 10 } });
  assert.equal(res.structuredContent.messages[0].thread_id, "35436");
  assert.equal(last.url.host, "acme.zendesk.com");
  assert.equal(last.url.searchParams.get("per_page"), "10");
  assert.equal(last.init.headers.Authorization, "Basic " + Buffer.from("jdoe@example.com/token:6wiIBWbG").toString("base64"));
});

test("zendesk: reply adds a public comment (wire)", async () => {
  let last;
  const client = await connect(SPEC, (url, init) => { last = { url, init }; return { body: { ticket: { id: 99 }, audit: { id: 555 } } }; });
  const res = await client.callTool({ name: "reply", arguments: { thread_id: "99", text: "Done" } });
  assert.equal(res.structuredContent.message_id, "555");
  assert.equal(last.init.method, "PUT");
  assert.deepEqual(JSON.parse(last.init.body), { ticket: { comment: { body: "Done", public: true } } });
});
