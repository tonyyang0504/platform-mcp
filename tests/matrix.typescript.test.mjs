import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/messaging/matrix.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  // `homeserver` is a non-secret config field: every tool path is https://{homeserver}/_matrix/client/...
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { access_token: "syt_secret_token", homeserver: "matrix.example.org" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("matrix: tools follow the messaging vocabulary (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_thread", "list_inbound", "mark_read", "me", "reply", "send"]);
  const li = tools.find((t) => t.name === "list_inbound");
  assert.equal(li.annotations.readOnlyHint, true);
  assert.equal(li.annotations.idempotentHint, true);
  assert.equal(li._meta["platform_mcp/endpoint"], "https://{homeserver}/_matrix/client/v3/rooms/{channel}/messages");
  assert.deepEqual(SPEC.adapter.not_offered, {});
});

test("matrix: me calls whoami on the configured homeserver with a bearer token (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { device_id: "ABC1234", user_id: "@joe:example.org" } }; });
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.ok, true);
  assert.equal(res.structuredContent.account.user_id, "@joe:example.org");
  assert.equal(seen.url.href, "https://matrix.example.org/_matrix/client/v3/account/whoami");
  assert.equal(seen.init.headers.Authorization, "Bearer syt_secret_token");
});

test("matrix: list_inbound reads one room backwards from the live edge (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { start: "t1", end: "t0", chunk: [
    { event_id: "$143273582443PhrSn:example.org", room_id: "!636q39766251:example.com", sender: "@example:example.org", type: "m.room.message", origin_server_ts: 1432735824653, content: { body: "This is an example text message", msgtype: "m.text" } },
    { event_id: "$state1:example.org", room_id: "!636q39766251:example.com", sender: "@example:example.org", type: "m.room.name", origin_server_ts: 1432735824000, content: { name: "The room name" } }] } }; });
  const res = await client.callTool({ name: "list_inbound", arguments: { channel: "!636q39766251:example.com", limit: 10 } });
  assert.equal(res.isError, false);
  const m = res.structuredContent.messages;
  assert.equal(m[0].id, "$143273582443PhrSn:example.org");
  assert.equal(m[0].from, "@example:example.org");
  assert.equal(m[0].text, "This is an example text message");
  assert.equal(m[0].thread_id, "!636q39766251:example.com");
  assert.equal(m[1].text, null);
  assert.equal(decodeURIComponent(seen.pathname), "/_matrix/client/v3/rooms/!636q39766251:example.com/messages");
  assert.equal(seen.searchParams.get("dir"), "b");
  assert.equal(seen.searchParams.get("limit"), "10");
  assert.equal(seen.searchParams.get("from"), null);
});

test("matrix: get_thread reads m.thread relations and needs the room id (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { chunk: [{ event_id: "$reply1:example.org", room_id: "!636q39766251:example.com", sender: "@bob:example.org", type: "m.room.message", content: { body: "reply in thread", msgtype: "m.text", "m.relates_to": { rel_type: "m.thread", event_id: "$root:example.org" } } }] } }; });
  let res = await client.callTool({ name: "get_thread", arguments: { thread_id: "$root:example.org", channel: "!636q39766251:example.com" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.messages[0].id, "$reply1:example.org");
  assert.equal(res.structuredContent.messages[0].text, "reply in thread");
  assert.equal(decodeURIComponent(seen.pathname), "/_matrix/client/v1/rooms/!636q39766251:example.com/relations/$root:example.org/m.thread");
  res = await client.callTool({ name: "get_thread", arguments: { thread_id: "$root:example.org" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "invalid_input");
});

test("matrix: unknown token is an auth_error result that does not leak the token (wire)", async () => {
  const client = await connect(() => ({ status: 401, body: { errcode: "M_UNKNOWN_TOKEN", error: "Unrecognised access token." } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.ok(!JSON.stringify(res.structuredContent).includes("syt_secret_token"));
});

test("matrix: send PUTs an m.text event under a fresh uuid txnId; mark_read accepts the empty answer (wire)", async () => {
  const log = [];
  const client = await connect((url, init) => { log.push({ url, init }); return init.method === "PUT" ? { body: { event_id: "$YUwRidLecu:example.com" } } : { body: {} }; });
  let res = await client.callTool({ name: "send", arguments: { to: "!636q39766251:example.com", text: "hello" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.message_id, "$YUwRidLecu:example.com");
  assert.deepEqual(JSON.parse(log[0].init.body), { msgtype: "m.text", body: "hello" });
  assert.match(decodeURIComponent(log[0].url.pathname), /^\/_matrix\/client\/v3\/rooms\/!636q39766251:example\.com\/send\/m\.room\.message\/[0-9a-f-]{36}$/);
  await client.callTool({ name: "send", arguments: { to: "!636q39766251:example.com", text: "again" } });
  assert.notEqual(log[0].url.pathname, log[1].url.pathname);
  res = await client.callTool({ name: "mark_read", arguments: { channel: "!636q39766251:example.com", message_id: "$YUwRidLecu:example.com" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "read");
  assert.equal(log[2].init.method, "POST");
  assert.equal(decodeURIComponent(log[2].url.pathname), "/_matrix/client/v3/rooms/!636q39766251:example.com/receipt/m.read/$YUwRidLecu:example.com");
  assert.equal(log[2].init.body, undefined);
});

test("matrix: reply sends a threaded event with m.relates_to (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { event_id: "$reply2:example.com" } }; });
  const res = await client.callTool({ name: "reply", arguments: { thread_id: "$root:example.org", channel: "!636q39766251:example.com", text: "in thread" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.message_id, "$reply2:example.com");
  assert.equal(seen.init.method, "PUT");
  assert.match(decodeURIComponent(seen.url.pathname), /^\/_matrix\/client\/v3\/rooms\/!636q39766251:example\.com\/send\/m\.room\.message\/[0-9a-f-]{36}$/);
  assert.deepEqual(JSON.parse(seen.init.body), { msgtype: "m.text", body: "in thread", "m.relates_to": { rel_type: "m.thread", event_id: "$root:example.org", is_falling_back: true, "m.in_reply_to": { event_id: "$root:example.org" } } });
});
