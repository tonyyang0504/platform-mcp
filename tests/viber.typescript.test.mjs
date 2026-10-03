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
const SPEC = JSON.parse(readFileSync(new URL("../catalog/messaging/viber.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_VIBER_AUTH_TOKEN: "445da6az1s345z78", PLATFORM_MCP_VIBER_SENDER_NAME: "Shop" });

test("viber: tools (wire)", async () => {
  assert.deepEqual(await names(SPEC), ["me", "send"]);
});

test("viber: send_message with sender.name and the auth header (wire)", async () => {
  let last;
  const client = await connect(SPEC, (url, init) => { last = { url, init }; return { body: { status: 0, status_message: "ok", message_token: "5741311803571721087" } }; });
  const res = await client.callTool({ name: "send", arguments: { to: "01234567890A=", text: "Hello" } });
  assert.equal(res.structuredContent.message_id, "5741311803571721087");
  assert.equal(res.structuredContent.status, "sent");
  assert.equal(last.url.href, "https://chatapi.viber.com/pa/send_message");
  assert.equal(last.init.headers["X-Viber-Auth-Token"], "445da6az1s345z78");
  assert.deepEqual(JSON.parse(last.init.body), { receiver: "01234567890A=", type: "text", text: "Hello", sender: { name: "Shop" } });
});

test("viber: get_account_info probe (wire)", async () => {
  const client = await connect(SPEC, () => ({ body: { status: 0, status_message: "ok", id: "pa:1", name: "Shop" } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.structuredContent.account.name, "Shop");
});

test("viber: non-zero status is an isError result (wire)", async () => {
  const client = await connect(SPEC, () => ({ body: { status: 6, status_message: "notSubscribed" } }));
  const res = await client.callTool({ name: "send", arguments: { to: "x", text: "y" } });
  assert.equal(res.isError, true);
  assert.match(res.structuredContent.message, /notSubscribed/);
});
