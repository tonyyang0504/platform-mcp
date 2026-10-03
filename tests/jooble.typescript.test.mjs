import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/jooble.json", import.meta.url), "utf8"));
const JOB = { id: 1234567890, title: "IT Support Specialist", location: "Bern", snippet: "Support the IT team ...", salary: "80'000 - 90'000 CHF", source: "jobs.ch", type: "Full-time", link: "https://jooble.org/desc/1234567890", company: "Acme AG", updated: "2026-09-20T00:00:00.0000000" };
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_key: "KEY123" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("tools follow the vocabulary and carry annotations (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name), ["search"]);
  assert.equal(tools[0].annotations.readOnlyHint, true);
  assert.equal(tools[0].annotations.destructiveHint, false);
  assert.deepEqual(tools[0].inputSchema.required, ["query"]);
  assert.equal(tools[0]._meta["platform_mcp/endpoint"], "/{api_key}");
  assert.ok(tools[0]._meta["platform_mcp/docs"].startsWith("https://help.jooble.org/"));
});

test("search posts the documented body with the key in the path (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { totalCount: 1, jobs: [JOB] } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "it", location: "Bern", page: 3, limit: 20 } });
  assert.equal(res.isError, false);
  const p = res.structuredContent.postings[0];
  assert.equal(p.id, "1234567890");
  assert.equal(p.title, "IT Support Specialist");
  assert.equal(p.company, "Acme AG");
  assert.equal(p.url, "https://jooble.org/desc/1234567890");
  assert.equal(p.description, "Support the IT team ...");
  assert.equal(p.raw.salary, "80'000 - 90'000 CHF");
  assert.equal(res.structuredContent.total, 1);
  assert.equal(seen.url.toString(), "https://jooble.org/api/KEY123");
  assert.equal(seen.init.method, "POST");
  assert.equal(seen.init.headers["Content-Type"], "application/json");
  assert.equal(seen.init.headers.Authorization, undefined);
  assert.deepEqual(JSON.parse(seen.init.body), { keywords: "it", location: "Bern", page: 3, ResultOnPage: 20 });
});

test("bad key is an isError auth_error result (wire)", async () => {
  const client = await connect(() => ({ status: 401, body: "Invalid key" }));
  const res = await client.callTool({ name: "search", arguments: { query: "it", location: "Bern" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.equal(res.structuredContent.http_status, 401);
});
