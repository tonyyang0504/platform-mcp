import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => ({ "content-type": "application/json" })[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/messaging/zalo.json", import.meta.url), "utf8"));
const CREDS = { app_id: "4318123456", secret_key: "ZALO-SECRET-abc", refresh_token: "RT-zalo-1" };

async function connect(handler) {
  const a = SPEC.adapter;
  const t = new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", fakeFetch(handler), a.envelope ?? {});
  const server = buildServer(SPEC, t);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return { client, t };
}

test("zalo (messaging): app_id refresh with secret_key header, access_token header, recent chats (wire)", async () => {
  const log = [];
  const { client, t } = await connect((url, init) => { log.push({ url, init });
    if (url.host === "oauth.zaloapp.com") return { body: { access_token: "AT-zalo-1", refresh_token: "RT-zalo-2", expires_in: "90000" } };
    return { body: { data: [{ src: 1, time: 1619401853770, message: "Chào shop", message_id: "92e5", from_id: "2512" }], error: 0, message: "Success" } }; });
  const res = await client.callTool({ name: "list_inbound", arguments: { limit: 3 } });
  assert.equal(res.isError, false); assert.equal(res.structuredContent.messages[0].id, "92e5");
  assert.deepEqual(Object.fromEntries(new URLSearchParams(String(log[0].init.body))), { grant_type: "refresh_token", refresh_token: "RT-zalo-1", app_id: "4318123456" });
  assert.equal(log[0].init.headers.secret_key, "ZALO-SECRET-abc");
  assert.equal(t.creds.refresh_token, "RT-zalo-2");
  assert.equal(log[1].init.headers.access_token, "AT-zalo-1");
  assert.deepEqual(JSON.parse(log[1].url.searchParams.get("data")), { offset: 0, count: 3 });
});

test("zalo (messaging): reply sends a consultation text; error codes are errors", async () => {
  const log = [];
  const { client } = await connect((url, init) => { log.push({ url, init });
    if (url.host === "oauth.zaloapp.com") return { body: { access_token: "AT", refresh_token: "RT2" } };
    if (url.pathname === "/v3.0/oa/message/cs") return { body: { data: { message_id: "m1" }, error: 0 } };
    return { body: { error: -216, message: "Access token is invalid" } }; });
  const r = await client.callTool({ name: "reply", arguments: { thread_id: "2512", text: "ok" } });
  assert.equal(r.structuredContent.message_id, "m1");
  assert.deepEqual(JSON.parse(log[1].init.body), { recipient: { user_id: "2512" }, message: { text: "ok" } });
  const e = await client.callTool({ name: "me", arguments: {} });
  assert.equal(e.isError, true);
});
