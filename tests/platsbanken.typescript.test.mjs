import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/platsbanken.json", import.meta.url), "utf8"));
const AD = { id: "31403584", headline: "Python Engineer", employer: { name: "Semicon Service Nordic AB" }, workplace_address: { municipality: "Malmö", country: "Sverige" }, webpage_url: "https://arbetsformedlingen.se/platsbanken/annonser/31403584", publication_date: "2026-08-27T10:01:50", description: { text: "Assignment Overview ..." }, application_details: { email: "hr@example.com", via_af: false } };
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
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_posting", "search"]);
  const gp = tools.find((t) => t.name === "get_posting");
  assert.equal(gp.annotations.readOnlyHint, true);
  assert.deepEqual(gp.inputSchema.required, ["id"]);
  assert.equal(gp._meta["platform_mcp/endpoint"], "/ad/{id}");
});

test("search maps q, remote, offset and limit without a credential (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { total: { value: 739 }, hits: [AD] } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "python", remote: true, page: 3, limit: 10 } });
  assert.equal(res.isError, false);
  const p = res.structuredContent.postings[0];
  assert.equal(p.id, "31403584");
  assert.equal(p.title, "Python Engineer");
  assert.equal(p.company, "Semicon Service Nordic AB");
  assert.equal(p.location, "Malmö");
  assert.equal(p.description, "Assignment Overview ...");
  assert.equal(res.structuredContent.total, 739);
  assert.equal(seen.url.searchParams.get("q"), "python");
  assert.equal(seen.url.searchParams.get("remote"), "true");
  assert.equal(seen.url.searchParams.get("offset"), "20");
  assert.equal(seen.url.searchParams.get("limit"), "10");
  assert.equal(seen.init.headers.Authorization, undefined);
});

test("get_posting maps the ad (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: AD }; });
  const res = await client.callTool({ name: "get_posting", arguments: { id: "31403584" } });
  assert.equal(res.isError, false);
  assert.equal(seen.pathname, "/ad/31403584");
  assert.equal(res.structuredContent.title, "Python Engineer");
  assert.equal(res.structuredContent.raw.application_details.email, "hr@example.com");
});

test("rate limit is an isError result, not a protocol error (wire)", async () => {
  const client = await connect(() => ({ status: 429, headers: { "Retry-After": "5" } }));
  const res = await client.callTool({ name: "search", arguments: { query: "python" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
  assert.equal(res.structuredContent.retry_after_seconds, 5);
});
