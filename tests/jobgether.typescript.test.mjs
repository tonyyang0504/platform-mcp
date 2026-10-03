import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/jobgether.json", import.meta.url), "utf8"));
const JOB = { id: "6ab4452d865119c687e37359", title: "AI Application Developer II", company: "CareSource", url: "https://jobgether.com/offer/6ab4452d865119c687e37359-ai-application-developer-ii", location: "Oregon (USA)", remote: "Full Remote", contractType: "Full time", experience: "Mid-level (2-5 years)", jobFunctions: ["AI Developer"], postedAt: "2026-09-23T21:31:25.954Z" };
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, {}, 50, "test", fakeFetch(handler)));
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
  assert.equal(tools[0]._meta["platform_mcp/endpoint"], "/api/v1/jobs");
});

test("search maps keyword, locations, page and limit (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { jobs: [JOB], pagination: { page: 2, limit: 10, hasMore: true } } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "python", location: "germany", page: 2, limit: 10 } });
  assert.equal(res.isError, false);
  const p = res.structuredContent.postings[0];
  assert.equal(p.id, "6ab4452d865119c687e37359");
  assert.equal(p.title, "AI Application Developer II");
  assert.equal(p.company, "CareSource");
  assert.equal(p.location, "Oregon (USA)");
  assert.equal(p.posted_at, "2026-09-23T21:31:25.954Z");
  assert.equal(p.raw.remote, "Full Remote");
  assert.equal(res.structuredContent.total, null);
  assert.equal(seen.url.searchParams.get("keyword"), "python");
  assert.equal(seen.url.searchParams.get("locations"), "germany");
  assert.equal(seen.url.searchParams.get("page"), "2");
  assert.equal(seen.url.searchParams.get("limit"), "10");
  assert.equal(seen.init.headers.Authorization, undefined);
});

test("limit is capped at the documented 25 (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { jobs: [], pagination: { page: 1, limit: 25, hasMore: false } } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "react", limit: 100 } });
  assert.equal(res.isError, false);
  assert.equal(seen.searchParams.get("limit"), "25");
});

test("unknown location slug is an isError upstream_error carrying the problem detail (wire)", async () => {
  const client = await connect(() => ({ status: 400, headers: { "content-type": "application/problem+json" }, body: { title: "Invalid parameter", status: 400, detail: "Invalid value for 'locations': \"Germany\"", field: "locations" } }));
  const res = await client.callTool({ name: "search", arguments: { query: "python", location: "Germany" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "invalid_input");
  assert.equal(res.structuredContent.http_status, 400);
  assert.ok(res.structuredContent.message.includes("Invalid value for 'locations'"));
});
