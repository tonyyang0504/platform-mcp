import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/unreal_forums_jobs.json", import.meta.url), "utf8"));
const TOPIC = { id: 613332, title: "[PAID] C++ gameplay programmer", created_at: "2026-09-20T20:16:46.860Z", excerpt: "We are looking", category_id: 76 };
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, {}, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("search scopes q to the Job Offerings category (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { posts: [], topics: [TOPIC] } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "programmer", page: 2 } });
  assert.equal(res.isError, false);
  assert.equal(seen.pathname, "/search.json");
  assert.equal(seen.searchParams.get("q"), "programmer #got-skills-looking-for-talent:job-offerings order:latest");
  assert.equal(seen.searchParams.get("page"), "2");
  assert.equal(res.structuredContent.postings[0].id, "613332");
});

test("get_posting reads the opening post (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { ...TOPIC, post_stream: { posts: [{ cooked: "<p>DM me</p>" }] } } }; });
  const res = await client.callTool({ name: "get_posting", arguments: { id: "613332" } });
  assert.equal(res.isError, false);
  assert.equal(seen.pathname, "/t/613332.json");
  assert.equal(res.structuredContent.description, "<p>DM me</p>");
});
