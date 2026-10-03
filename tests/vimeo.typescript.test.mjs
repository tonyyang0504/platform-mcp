import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/vimeo.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { access_token: "vimeo-secret-token" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("vimeo: read_comments maps data[] with page/per_page (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { total: 1, data: [{ uri: "/videos/9/comments/1", text: "hi", created_on: "2026-09-01T00:00:00+00:00", user: { name: "Ann" } }] } }; });
  const res = await client.callTool({ name: "read_comments", arguments: { post_id: "9", page: 1, limit: 10 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.comments[0].author, "Ann");
  assert.equal(seen.url.pathname, "/videos/9/comments");
  assert.equal(seen.url.searchParams.get("per_page"), "10");
  assert.equal(seen.init.headers.Authorization, "Bearer vimeo-secret-token");
});
