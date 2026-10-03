import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/devto.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_key: "k" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("devto read_comments sends the api-key header and maps id_code (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: [{ type_of: "comment", id_code: "abc1", created_at: "2026-09-01T10:00:00Z", children: [] }] }; });
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["analytics_post", "me", "read_comments"]);
  const res = await client.callTool({ name: "read_comments", arguments: { post_id: "321" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.comments[0].id, "abc1");
  assert.equal(seen.url.searchParams.get("a_id"), "321");
  assert.equal(seen.url.searchParams.get("per_page"), "30");
  assert.equal(seen.init.headers["api-key"], "k");
});

test("devto 401 is an auth_error result (wire)", async () => {
  const client = await connect(() => ({ status: 401, body: { error: "unauthorized" } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
});
