import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/nextdoor.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { access_token: "nd-secret-token" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("nextdoor: publish_text posts body_text with bearer (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { result: "success", share_link: "https://nextdoor.com/p/abc" } }; });
  const res = await client.callTool({ name: "publish_text", arguments: { text: "hi" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.url, "https://nextdoor.com/p/abc");
  assert.equal(seen.url.href, "https://nextdoor.com/external/api/partner/v1/post/create/");
  assert.deepEqual(JSON.parse(seen.init.body), { body_text: "hi" });
  assert.equal(seen.init.headers.Authorization, "Bearer nd-secret-token");
});

test("nextdoor: delete sends the id query parameter (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { message: "Post deleted successfully" } }; });
  const res = await client.callTool({ name: "delete", arguments: { post_id: "p1" } });
  assert.equal(res.isError, false);
  assert.equal(seen.init.method, "DELETE");
  assert.equal(seen.url.searchParams.get("id"), "p1");
});
