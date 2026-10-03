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
const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/pinterest.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_PINTEREST_CLIENT_ID: "1234", PLATFORM_MCP_PINTEREST_CLIENT_SECRET: "sec", PLATFORM_MCP_PINTEREST_REFRESH_TOKEN: "pinr.1", PLATFORM_MCP_PINTEREST_BOARD_ID: "549755885175" });
const TOKEN = "https://api.pinterest.com/v5/oauth/token";
const tok = { body: { access_token: "pina.A", expires_in: 2592000 } };

test("pinterest (social): tools (wire)", async () => {
  assert.deepEqual(await names(SPEC), ["analytics_post", "delete", "me", "publish_image"]);
});

test("pinterest (social): publish_image creates an image_url Pin with a Basic token request (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return url.href === TOKEN ? tok : { status: 201, body: { id: "8137", created_at: "2026-09-24T00:00:00" } }; });
  const res = await client.callTool({ name: "publish_image", arguments: { text: "New drop", image_urls: ["https://img/a.jpg"] } });
  assert.equal(res.structuredContent.id, "8137");
  assert.match(seen[0].init.headers.Authorization, /^Basic /);
  assert.deepEqual(JSON.parse(seen[1].init.body), { board_id: "549755885175", description: "New drop", media_source: { source_type: "image_url", url: "https://img/a.jpg" } });
});

test("pinterest (social): pin_metrics analytics (wire)", async () => {
  let last;
  const client = await connect(SPEC, (url) => { if (url.href === TOKEN) return tok; last = url; return { body: { id: "81", pin_metrics: { "90d": { impression: 2 } } } }; });
  const res = await client.callTool({ name: "analytics_post", arguments: { post_id: "81" } });
  assert.deepEqual(res.structuredContent.metrics, { "90d": { impression: 2 } });
  assert.equal(last.searchParams.get("pin_metrics"), "true");
});
