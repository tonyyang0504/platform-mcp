import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/telegram.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { token: "123:ABC", chat_id: "@mychannel" }, 50, "test", fakeFetch(handler), SPEC.adapter.envelope));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("telegram (social): publish_text posts to the configured chat_id with the token in the path (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { ok: true, result: { message_id: 42, date: 1758700000, chat: { id: -1001, type: "channel" }, text: "hello" } } }; });
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["delete", "me", "publish_image", "publish_text"]);
  const res = await client.callTool({ name: "publish_text", arguments: { text: "hello", reply_to: "7" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "42");
  assert.equal(seen.url.href, "https://api.telegram.org/bot123:ABC/sendMessage");
  assert.deepEqual(JSON.parse(seen.init.body), { chat_id: "@mychannel", text: "hello", reply_parameters: { message_id: "7" } });
  assert.equal(seen.init.headers.Authorization, undefined);
  const img = await client.callTool({ name: "publish_image", arguments: { text: "pic", image_urls: ["https://img.example/a.png", "https://img.example/b.png"] } });
  assert.equal(img.isError, false);
  assert.equal(seen.url.href, "https://api.telegram.org/bot123:ABC/sendPhoto");
  assert.deepEqual(JSON.parse(seen.init.body), { chat_id: "@mychannel", photo: "https://img.example/a.png", caption: "pic" });
});

test("telegram (social): delete answers a literal status and ok:false is an error (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: JSON.parse(init.body).message_id === "42" ? { ok: true, result: true } : { ok: false, error_code: 400, description: "Bad Request: message to delete not found" } }; });
  const res = await client.callTool({ name: "delete", arguments: { post_id: "42" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "deleted");
  assert.equal(seen.url.href, "https://api.telegram.org/bot123:ABC/deleteMessage");
  assert.deepEqual(JSON.parse(seen.init.body), { chat_id: "@mychannel", message_id: "42" });
  const bad = await client.callTool({ name: "delete", arguments: { post_id: "1" } });
  assert.equal(bad.isError, true);
  assert.equal(bad.structuredContent.error, "upstream_error");
});
