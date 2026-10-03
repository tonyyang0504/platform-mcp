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
const SPEC = JSON.parse(readFileSync(new URL("../catalog/messaging/wecom.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_WECOM_CORPID: "ww1", PLATFORM_MCP_WECOM_CORPSECRET: "csec", PLATFORM_MCP_WECOM_AGENT_ID: "1000002" });
const tokenOk = { body: { errcode: 0, errmsg: "ok", access_token: "accesstoken000001", expires_in: 7200 } };

test("wecom: tools (wire)", async () => {
  assert.deepEqual(await names(SPEC), ["me", "send"]);
});

test("wecom: GET login, token as access_token query parameter, integer agentid (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return url.pathname.endsWith("/gettoken") ? tokenOk : { body: { errcode: 0, errmsg: "ok", msgid: "xx1" } }; });
  const res = await client.callTool({ name: "send", arguments: { to: "UserID1", text: "hi" } });
  assert.equal(res.structuredContent.message_id, "xx1");
  assert.equal(seen[0].url.searchParams.get("corpid"), "ww1");
  assert.equal(seen[0].url.searchParams.get("corpsecret"), "csec");
  assert.equal(seen[1].url.searchParams.get("access_token"), "accesstoken000001");
  assert.equal(seen[1].init.headers.Authorization, undefined);
  assert.deepEqual(JSON.parse(seen[1].init.body), { touser: "UserID1", msgtype: "text", agentid: 1000002, text: { content: "hi" } });
});

test("wecom: errcode inside HTTP 200 is an isError result (wire)", async () => {
  const client = await connect(SPEC, (url) => url.pathname.endsWith("/gettoken") ? tokenOk : { body: { errcode: 42001, errmsg: "access_token expired" } });
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
});
