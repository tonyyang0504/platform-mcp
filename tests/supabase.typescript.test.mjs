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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/builder_tools/supabase.json", import.meta.url), "utf8"));
Object.assign(process.env, {"PLATFORM_MCP_SUPABASE_SECRET_KEY": "sb_secret_abc", "PLATFORM_MCP_SUPABASE_PROJECT_REF": "abcd1234"});

test("supabase create_item: array insert body, apikey header, Prefer (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { status: 201, body: [{ id: 9, title: "new" }] }; });
  const res = await client.callTool({ name: "create_item", arguments: { collection: "todos", fields: { title: "new" } } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].url.href, "https://abcd1234.supabase.co/rest/v1/todos");
  assert.equal(seen[0].init.headers.apikey, "sb_secret_abc");
  assert.equal(seen[0].init.headers.Prefer, "return=representation");
  assert.deepEqual(body(seen[0].init), [{ title: "new" }]);
  assert.equal(res.structuredContent.id, "9");
});

test("supabase update_item: upsert with id merged into the row (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: [{ id: 9, done: true }] }; });
  await client.callTool({ name: "update_item", arguments: { collection: "todos", item_id: "9", fields: { done: true } } });
  assert.deepEqual(body(seen[0].init), [{ done: true, id: "9" }]);
  assert.match(seen[0].init.headers.Prefer, /^resolution=merge-duplicates/);
});
