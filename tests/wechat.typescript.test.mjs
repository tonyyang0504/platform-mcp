import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/wechat.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_WECHAT_APPID: "wx123", PLATFORM_MCP_WECHAT_SECRET: "wechat-app-secret" });
const tokenOk = { body: { access_token: "wxaccesstoken0001", expires_in: 7200 } };

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("wechat: publish_text mass-sends with access_token query (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => { seen.push({ url, init }); return url.pathname.endsWith("/token") ? tokenOk : { body: { errcode: 0, errmsg: "ok", msg_id: 34182 } }; });
  const res = await client.callTool({ name: "publish_text", arguments: { text: "hi" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "34182");
  assert.equal(seen[0].url.searchParams.get("grant_type"), "client_credential");
  const send = seen.find((s) => s.url.pathname.endsWith("/message/mass/sendall"));
  assert.equal(send.url.searchParams.get("access_token"), "wxaccesstoken0001");
  assert.deepEqual(JSON.parse(send.init.body), { filter: { is_to_all: true }, msgtype: "text", text: { content: "hi" } });
});

test("wechat: non-zero errcode is an error result (wire)", async () => {
  const client = await connect((url) => url.pathname.endsWith("/token") ? tokenOk : { body: { errcode: 45028, errmsg: "has no masssend quota" } });
  const res = await client.callTool({ name: "publish_text", arguments: { text: "hi" } });
  assert.equal(res.isError, true);
});
