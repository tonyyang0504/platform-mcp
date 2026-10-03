import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (r.raw ?? JSON.stringify(r.body ?? {})) }; };
async function connect(spec, handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(spec);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}
const body = (init) => JSON.parse(init.body);

const SPEC = JSON.parse(readFileSync(new URL("../catalog/builder_tools/elevenlabs.json", import.meta.url), "utf8"));
Object.assign(process.env, {"PLATFORM_MCP_ELEVENLABS_API_KEY": "xi-secret"});

test("elevenlabs list_items: /v2/voices cursor paging with xi-api-key (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { voices: [{ voice_id: "v1", name: "Rachel" }], has_more: true, next_page_token: "tok2", total_count: 40 } }; });
  const res = await client.callTool({ name: "list_items", arguments: { limit: 10, cursor: "tok1" } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].url.searchParams.get("page_size"), "10");
  assert.equal(seen[0].url.searchParams.get("next_page_token"), "tok1");
  assert.equal(seen[0].init.headers["xi-api-key"], "xi-secret");
  assert.equal(res.structuredContent.next_cursor, "tok2");
  assert.equal(res.structuredContent.items[0].id, "v1");
});

test("elevenlabs delete_item: DELETE /v1/voices/{id} (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { status: "ok" } }; });
  const res = await client.callTool({ name: "delete_item", arguments: { item_id: "v1" } });
  assert.equal(seen[0].init.method, "DELETE");
  assert.equal(seen[0].url.pathname, "/v1/voices/v1");
  assert.equal(res.structuredContent.status, "ok");
});
