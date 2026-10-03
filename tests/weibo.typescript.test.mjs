import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/weibo.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { access_token: "2.00weibo-secret", user_ip: "211.156.0.1" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("weibo: publish_text posts a form body with rip and access_token query (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { idstr: "350", created_at: "Wed Oct 24 23:49:17 +0800 2012" } }; });
  const res = await client.callTool({ name: "publish_text", arguments: { text: "hi https://example.com" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, "350");
  assert.equal(seen.url.pathname, "/2/statuses/share.json");
  assert.equal(seen.url.searchParams.get("access_token"), "2.00weibo-secret");
  const form = Object.fromEntries(new URLSearchParams(String(seen.init.body)));
  assert.deepEqual(form, { status: "hi https://example.com", rip: "211.156.0.1" });
});
