import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/facebook.json", import.meta.url), "utf8"));
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

process.env.PLATFORM_MCP_FACEBOOK_PAGE_ACCESS_TOKEN = "PAGE-TOKEN";
process.env.PLATFORM_MCP_FACEBOOK_PAGE_ID = "1234";

test("facebook publish_text posts to /{page_id}/feed with the Page token (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { id: "1234_5678" } }; });
  const { tools } = await client.listTools();
  assert.equal(tools.length, 8);
  const res = await client.callTool({ name: "publish_text", arguments: { text: "hello page" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "1234_5678");
  assert.equal(seen.url.href, "https://graph.facebook.com/v26.0/1234/feed");
  assert.deepEqual(JSON.parse(seen.init.body), { message: "hello page" });
  assert.equal(seen.init.headers.Authorization, "Bearer PAGE-TOKEN");
});

test("facebook read_mentions reads /{page_id}/tagged (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { data: [{ id: "9_1", message: "hi @page", tagged_time: "2026-09-24T00:00:00+0000" }] } }; });
  const res = await client.callTool({ name: "read_mentions", arguments: {} });
  assert.equal(res.isError, false);
  assert.equal(seen.pathname, "/v26.0/1234/tagged");
  assert.equal(res.structuredContent.mentions[0].text, "hi @page");
});
