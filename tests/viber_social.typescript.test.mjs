import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/viber.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { auth_token: "viber-channel-secret", sender_id: "01234567890A=" }, 50, "test", fakeFetch(handler), a.envelope));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("viber social: publish_text posts to the channel (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { status: 0, status_message: "ok", message_token: 42 } }; });
  const res = await client.callTool({ name: "publish_text", arguments: { text: "hi" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "42");
  assert.equal(seen.url.href, "https://chatapi.viber.com/pa/post");
  assert.deepEqual(JSON.parse(seen.init.body), { auth_token: "viber-channel-secret", from: "01234567890A=", type: "text", text: "hi" });
});

test("viber social: status 10 is an error result (wire)", async () => {
  const client = await connect(() => ({ body: { status: 10, status_message: "webhookNotSet" } }));
  const res = await client.callTool({ name: "publish_text", arguments: { text: "hi" } });
  assert.equal(res.isError, true);
});
