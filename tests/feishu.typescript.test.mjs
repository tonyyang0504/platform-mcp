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
const SPEC = JSON.parse(readFileSync(new URL("../catalog/messaging/feishu.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_FEISHU_APP_ID: "cli_x", PLATFORM_MCP_FEISHU_APP_SECRET: "sec", PLATFORM_MCP_FEISHU_RECEIVE_ID_TYPE: "chat_id" });
const LOGIN = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal";

test("feishu: tools (wire)", async () => {
  assert.deepEqual(await names(SPEC), ["get_thread", "list_inbound", "me", "reply", "send"]);
});

test("feishu: tenant token login then chat history (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return url.href === LOGIN ? { body: { code: 0, tenant_access_token: "t-abc", expire: 7200 } } : { body: { code: 0, data: { items: [{ message_id: "om_1", sender: { id: "ou_1" }, body: { content: "{\"text\":\"hi\"}" }, create_time: "1615380573411" }] } } }; });
  const res = await client.callTool({ name: "list_inbound", arguments: { channel: "oc_1" } });
  assert.equal(res.structuredContent.messages[0].id, "om_1");
  assert.deepEqual(JSON.parse(seen[0].init.body), { app_id: "cli_x", app_secret: "sec" });
  assert.equal(seen[1].init.headers.Authorization, "Bearer t-abc");
  assert.equal(seen[1].url.searchParams.get("container_id_type"), "chat");
  assert.equal(seen[1].url.searchParams.get("container_id"), "oc_1");
});

test("feishu: get_thread uses the thread container (wire)", async () => {
  let last;
  const client = await connect(SPEC, (url, init) => { if (url.href === LOGIN) return { body: { tenant_access_token: "t-abc", expire: 7200 } }; last = url; return { body: { data: { items: [] } } }; });
  const res = await client.callTool({ name: "get_thread", arguments: { thread_id: "omt_1" } });
  assert.deepEqual(res.structuredContent.messages, []);
  assert.equal(last.searchParams.get("container_id_type"), "thread");
});

test("feishu: non-zero code is an isError result (wire)", async () => {
  const client = await connect(SPEC, (url) => url.href === LOGIN ? { body: { code: 0, tenant_access_token: "t-abc", expire: 7200 } } : { body: { code: 230002, msg: "Bot/User can NOT be out of the chat." } });
  const res = await client.callTool({ name: "list_inbound", arguments: { channel: "oc_x" } });
  assert.equal(res.isError, true);
});

test("feishu: send serializes content as an escaped JSON string (wire)", async () => {
  let last;
  const client = await connect(SPEC, (url, init) => { if (url.href === LOGIN) return { body: { code: 0, tenant_access_token: "t-abc", expire: 7200 } }; last = { url, init }; return { body: { code: 0, data: { message_id: "om_9" } } }; });
  const text = 'He said "hi"\nand left';
  const res = await client.callTool({ name: "send", arguments: { to: "oc_1", text } });
  assert.equal(res.structuredContent.message_id, "om_9");
  assert.equal(last.url.searchParams.get("receive_id_type"), "chat_id");
  const body = JSON.parse(last.init.body);
  assert.equal(typeof body.content, "string");
  assert.deepEqual(JSON.parse(body.content), { text });
});
