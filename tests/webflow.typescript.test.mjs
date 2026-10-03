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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/builder_tools/webflow.json", import.meta.url), "utf8"));
Object.assign(process.env, {"PLATFORM_MCP_WEBFLOW_TOKEN": "wf-secret"});

test("webflow create_item: fieldData with name from title (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { status: 202, body: { id: "i2", isDraft: false } }; });
  const res = await client.callTool({ name: "create_item", arguments: { collection: "c1", title: "Hello", fields: { slug: "hello" } } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].url.href, "https://api.webflow.com/v2/collections/c1/items");
  assert.equal(seen[0].init.headers.Authorization, "Bearer wf-secret");
  assert.deepEqual(body(seen[0].init), { fieldData: { slug: "hello", name: "Hello" } });
});

test("webflow list_items: offset paging and total (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { items: [{ id: "i1", fieldData: { name: "Post", slug: "post" } }], pagination: { limit: 10, offset: 10, total: 11 } } }; });
  const res = await client.callTool({ name: "list_items", arguments: { collection: "c1", page: 2, limit: 10 } });
  assert.equal(seen[0].url.searchParams.get("offset"), "10");
  assert.equal(res.structuredContent.total, 11);
  assert.equal(res.structuredContent.items[0].title, "Post");
});
