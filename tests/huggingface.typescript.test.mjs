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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/builder_tools/huggingface.json", import.meta.url), "utf8"));
Object.assign(process.env, {"PLATFORM_MCP_HUGGINGFACE_TOKEN": "hf_secret"});

test("huggingface create_item: /api/repos/create with mapped type (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { url: "https://huggingface.co/spaces/me/demo", name: "me/demo", id: "0123456789abcdef01234567" } }; });
  const res = await client.callTool({ name: "create_item", arguments: { collection: "spaces", title: "demo", fields: { private: true, sdk: "gradio" } } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].init.headers.Authorization, "Bearer hf_secret");
  assert.deepEqual(body(seen[0].init), { type: "space", name: "demo", private: true, sdk: "gradio" });
  assert.equal(res.structuredContent.id, "me/demo");
});

test("huggingface get_item: repo id with slash stays in the path (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { id: "google/gemma-2b" } }; });
  await client.callTool({ name: "get_item", arguments: { item_id: "google/gemma-2b" } });
  assert.equal(seen[0].url.pathname, "/api/models/google/gemma-2b");
});
