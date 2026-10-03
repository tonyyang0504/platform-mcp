import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/messaging/instagram_dm.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

process.env.PLATFORM_MCP_INSTAGRAM_DM_PAGE_ACCESS_TOKEN = "PAGE-TOKEN";
process.env.PLATFORM_MCP_INSTAGRAM_DM_PAGE_ID = "1234";

test("instagram_dm send addresses the IGSID (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { recipient_id: "IGSID1", message_id: "aWd1" } }; });
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_thread", "list_inbound", "me", "send"]);
  const res = await client.callTool({ name: "send", arguments: { to: "IGSID1", text: "hi" } });
  assert.equal(res.isError, false);
  assert.deepEqual(JSON.parse(seen.init.body), { recipient: { id: "IGSID1" }, message: { text: "hi" } });
});

test("instagram_dm get_thread maps usernames (wire)", async () => {
  const client = await connect(() => ({ body: { data: [{ id: "aWd2", message: "Hi Kitty!", from: { username: "fan", id: "IGSID1" }, to: { data: [{ username: "shop", id: "17841" }] }, created_time: "2022-07-12T19:11:07+0000" }] } }));
  const res = await client.callTool({ name: "get_thread", arguments: { thread_id: "c_1" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.messages[0].from, "fan");
  assert.equal(res.structuredContent.messages[0].to, "shop");
});
