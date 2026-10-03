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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/builder_tools/runway.json", import.meta.url), "utf8"));
Object.assign(process.env, {"PLATFORM_MCP_RUNWAY_API_KEY": "rw-secret"});

test("runway generate_image: text_to_image body and version header (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { id: "11111111-1111-4111-8111-111111111111", estimatedCost: { credits: 5 } } }; });
  const res = await client.callTool({ name: "generate_image", arguments: { prompt: "a lamp", model: "gen4_image", aspect_ratio: "1920:1080", image_url: "https://x/ref.png" } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].url.href, "https://api.dev.runwayml.com/v1/text_to_image");
  assert.equal(seen[0].init.headers["X-Runway-Version"], "2024-11-06");
  assert.deepEqual(body(seen[0].init), { model: "gen4_image", promptText: "a lamp", ratio: "1920:1080", referenceImages: [{ uri: "https://x/ref.png" }] });
});

test("runway list_items: documents with cursor (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { data: [{ id: "d1", name: "FAQ" }], hasMore: false, nextCursor: null } }; });
  const res = await client.callTool({ name: "list_items", arguments: { cursor: "c1", limit: 10 } });
  assert.equal(seen[0].url.searchParams.get("cursor"), "c1");
  assert.equal(res.structuredContent.items[0].title, "FAQ");
  assert.equal(res.structuredContent.next_cursor, null);
});
