import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/remote_ok.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

// https://remoteok.com/api (opened 2026-09-24): bare array, element 0 is the legal notice
const FEED = [
  { last_updated: 1790208007, legal: "API Terms of Service: Please link back (with follow, and without nofollow!) to the URL on Remote OK and mention Remote OK as a source" },
  { slug: "remote-technical-product-manager-ai-stockbroking-app-bjak-1137421", id: "1137421", epoch: 1790121610, date: "2026-09-23T00:00:10+00:00", company: "Bjak ", position: "Technical Product Manager AI Stockbroking App", tags: ["product manager", "exec"], description: "<p>About KIRA</p>", location: "Worldwide", apply_url: "https://remoteok.com/remote-jobs/x-1137421", salary_min: 40000, salary_max: 70000, url: "https://remoteok.com/remote-jobs/x-1137421" },
];

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, {}, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("remote_ok: only search_postings is offered (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name), ["search_postings"]);
  assert.equal(tools[0].annotations.readOnlyHint, true);
  assert.equal(tools[0].title, "Search postings");
  assert.equal(tools[0]._meta["platform_mcp/endpoint"], "/api");
});

test("remote_ok: search maps the feed and sends no parameters (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: FEED }; });
  const res = await client.callTool({ name: "search_postings", arguments: { query: "python" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.postings.length, 1); // the legal notice (id null) is dropped by require: [id]
  const [job] = res.structuredContent.postings;
  assert.equal(job.id, "1137421");
  assert.equal(job.title, "Technical Product Manager AI Stockbroking App");
  assert.equal(job.buyer, "Bjak ");
  assert.equal(job.budget_max, 70000);
  assert.deepEqual(job.skills, ["product manager", "exec"]);
  assert.equal(res.structuredContent.next_page, null);
  assert.equal(seen.href, "https://remoteok.com/api");
});

test("remote_ok: 429 is a rate_limited isError result (wire)", async () => {
  const client = await connect(() => ({ status: 429, headers: { "Retry-After": "5" }, body: {} }));
  const res = await client.callTool({ name: "search_postings", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
  assert.equal(res.structuredContent.retry_after_seconds, 5);
});
