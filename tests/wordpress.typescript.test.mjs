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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/builder_tools/wordpress.json", import.meta.url), "utf8"));
Object.assign(process.env, {"PLATFORM_MCP_WORDPRESS_USERNAME": "editor", "PLATFORM_MCP_WORDPRESS_APPLICATION_PASSWORD": "abcd efgh ijkl", "PLATFORM_MCP_WORDPRESS_SITE": "blog.example.com"});

test("wordpress create_item: post body with Basic application password (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { status: 201, body: { id: 44, link: "https://blog.example.com/?p=44", status: "draft" } }; });
  const res = await client.callTool({ name: "create_item", arguments: { title: "About", content: "<p>Hi</p>", fields: { status: "draft" } } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].url.href, "https://blog.example.com/wp-json/wp/v2/posts");
  assert.equal(seen[0].init.headers.Authorization, "Basic " + Buffer.from("editor:abcd efgh ijkl").toString("base64"));
  assert.deepEqual(body(seen[0].init), { title: "About", content: "<p>Hi</p>", status: "draft" });
  assert.equal(res.structuredContent.id, "44");
});

test("wordpress delete_item: DELETE moves to trash (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { id: 1, status: "trash" } }; });
  const res = await client.callTool({ name: "delete_item", arguments: { collection: "pages", item_id: "1" } });
  assert.equal(seen[0].init.method, "DELETE");
  assert.equal(seen[0].url.pathname, "/wp-json/wp/v2/pages/1");
  assert.equal(res.structuredContent.status, "trash");
});
