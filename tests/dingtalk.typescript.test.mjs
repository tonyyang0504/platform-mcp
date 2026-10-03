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
const SPEC = JSON.parse(readFileSync(new URL("../catalog/messaging/dingtalk.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_DINGTALK_APP_KEY: "dingkey", PLATFORM_MCP_DINGTALK_APP_SECRET: "dingsec", PLATFORM_MCP_DINGTALK_ROBOT_CODE: "dingrobot" });
const LOGIN = "https://api.dingtalk.com/v1.0/oauth2/accessToken";

test("dingtalk: only send is served (wire)", async () => {
  assert.deepEqual(await names(SPEC), ["send"]);
});

test("dingtalk: token header and serialized msgParam (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return url.href === LOGIN ? { body: { accessToken: "fw8ef", expireIn: 7200 } } : { body: { processQueryKey: "zcxx" } }; });
  const text = 'say "hi"\nbye';
  const res = await client.callTool({ name: "send", arguments: { to: "manager1234", text } });
  assert.equal(res.structuredContent.message_id, "zcxx");
  assert.deepEqual(JSON.parse(seen[0].init.body), { appKey: "dingkey", appSecret: "dingsec" });
  assert.equal(seen[1].init.headers["x-acs-dingtalk-access-token"], "fw8ef");
  const body = JSON.parse(seen[1].init.body);
  assert.deepEqual(body.userIds, ["manager1234"]);
  assert.equal(body.msgKey, "sampleText");
  assert.deepEqual(JSON.parse(body.msgParam), { content: text });
});

test("dingtalk: 400 is an isError result (wire)", async () => {
  const client = await connect(SPEC, (url) => url.href === LOGIN ? { body: { accessToken: "fw8ef", expireIn: 7200 } } : { status: 400, body: { code: "invalidParameter.msgParam.invalid" } });
  const res = await client.callTool({ name: "send", arguments: { to: "u", text: "x" } });
  assert.equal(res.isError, true);
});
