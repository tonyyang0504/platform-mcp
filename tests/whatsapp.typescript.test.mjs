import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/messaging/whatsapp.json", import.meta.url), "utf8"));
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

process.env.PLATFORM_MCP_WHATSAPP_ACCESS_TOKEN = "SYS-TOKEN";
process.env.PLATFORM_MCP_WHATSAPP_PHONE_NUMBER_ID = "106540352242922";

test("whatsapp send posts a text message and returns the wamid (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { messaging_product: "whatsapp", contacts: [{ input: "+16505551234", wa_id: "16505551234" }], messages: [{ id: "wamid.ABC" }] } }; });
  const res = await client.callTool({ name: "send", arguments: { to: "+16505551234", text: "hello" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.message_id, "wamid.ABC");
  assert.equal(seen.url.href, "https://graph.facebook.com/v26.0/106540352242922/messages");
  assert.deepEqual(JSON.parse(seen.init.body), { messaging_product: "whatsapp", recipient_type: "individual", to: "+16505551234", type: "text", text: { body: "hello" } });
  assert.equal(seen.init.headers.Authorization, "Bearer SYS-TOKEN");
});

test("whatsapp mark_read sends status read (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = init; return { body: { success: true } }; });
  const res = await client.callTool({ name: "mark_read", arguments: { message_id: "wamid.X" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "ok");
  assert.deepEqual(JSON.parse(seen.body), { messaging_product: "whatsapp", status: "read", message_id: "wamid.X" });
});
