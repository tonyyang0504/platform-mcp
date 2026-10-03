import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/threads.json", import.meta.url), "utf8"));
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

process.env.PLATFORM_MCP_THREADS_ACCESS_TOKEN = "TH-TOKEN";

test("threads publish_text is one form call with auto_publish_text and the token as a query parameter (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { id: "1234567" } }; });
  const res = await client.callTool({ name: "publish_text", arguments: { text: "hello" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "1234567");
  assert.equal(seen.url.pathname, "/v1.0/me/threads");
  assert.equal(seen.url.searchParams.get("access_token"), "TH-TOKEN");
  assert.deepEqual(Object.fromEntries(new URLSearchParams(seen.init.body)), { media_type: "TEXT", text: "hello", auto_publish_text: "true" });
});

test("threads read_mentions maps /me/mentions (wire)", async () => {
  const client = await connect(() => ({ body: { data: [{ id: "5", text: "@me hi", username: "amy", timestamp: "2026-09-24T00:00:00+0000" }] } }));
  const res = await client.callTool({ name: "read_mentions", arguments: {} });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.mentions[0].author, "amy");
});
