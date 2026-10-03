import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/messaging/kakao.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
Object.assign(process.env, { PLATFORM_MCP_KAKAO_CLIENT_ID: "restapikey1", PLATFORM_MCP_KAKAO_CLIENT_SECRET: "kakao-client-secret", PLATFORM_MCP_KAKAO_REFRESH_TOKEN: "kakao-refresh-token-1", PLATFORM_MCP_KAKAO_LINK_URL: "https://shop.example.com" });

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("kakao: send mints a token and posts the text template as form fields (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => { seen.push({ url, init }); return url.host === "kauth.kakao.com" ? { body: { access_token: "kakao-access-0001", expires_in: 43199 } } : { body: { successful_receiver_uuids: ["u1"] } }; });
  const res = await client.callTool({ name: "send", arguments: { to: "u1", text: "hi" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "sent");
  const send = seen.find((s) => s.url.pathname === "/v1/api/talk/friends/message/default/send");
  assert.equal(send.init.headers.Authorization, "Bearer kakao-access-0001");
  const form = Object.fromEntries(new URLSearchParams(String(send.init.body)));
  assert.deepEqual(JSON.parse(form.receiver_uuids), ["u1"]);
  assert.deepEqual(JSON.parse(form.template_object), { object_type: "text", text: "hi", link: { web_url: "https://shop.example.com", mobile_web_url: "https://shop.example.com" } });
});
