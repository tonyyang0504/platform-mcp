import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/getonbrd.json", import.meta.url), "utf8"));
const HIT = { id: "web-app-full-stack-engineer-niuro-remote-4461", type: "job", attributes: { title: "Web App Full-Stack Engineer", description: "<p>Build ...</p>", remote: true, countries: ["Remote"], min_salary: 2500, max_salary: 4000, published_at: 1790253211, company: { data: { id: "niuro", type: "company", attributes: { name: "Niuro" } } } }, links: { public_url: "https://www.getonbrd.com/jobs/web-app-full-stack-engineer-niuro-remote-4461" } };
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
  assert.deepEqual(tools[0].inputSchema.required, ["query"]);
  assert.equal(tools[0]._meta["platform_mcp/endpoint"], "/api/v0/search/jobs");
  assert.equal(tools[0]._meta["platform_mcp/docs"], "https://www.getonbrd.com/api-doc.html");
});

test("search maps JSON:API hits and expands the company (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { data: [HIT], meta: { page: 2, per_page: 30, total_pages: 310 } } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "developer", remote: true, page: 2, limit: 30 } });
  assert.equal(res.isError, false);
  const p = res.structuredContent.postings[0];
  assert.equal(p.id, "web-app-full-stack-engineer-niuro-remote-4461");
  assert.equal(p.title, "Web App Full-Stack Engineer");
  assert.equal(p.company, "Niuro");
  assert.equal(p.location, "Remote");
  assert.equal(p.url, "https://www.getonbrd.com/jobs/web-app-full-stack-engineer-niuro-remote-4461");
  assert.equal(p.salary_min, 2500);
  assert.equal(p.raw.attributes.published_at, 1790253211);
  assert.equal(res.structuredContent.total, null);
  assert.equal(seen.url.searchParams.get("query"), "developer");
  assert.equal(seen.url.searchParams.get("remote"), "true");
  assert.equal(seen.url.searchParams.get("page"), "2");
  assert.equal(seen.url.searchParams.get("per_page"), "30");
  assert.equal(seen.url.searchParams.get("expand"), '["company"]');
  assert.equal(seen.init.headers.Authorization, undefined);
});

test("unprocessable search is an isError upstream_error result (wire)", async () => {
  const client = await connect(() => ({ status: 422, body: { message: "unprocessable_content" } }));
  const res = await client.callTool({ name: "search", arguments: { query: "" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "invalid_input");
  assert.equal(res.structuredContent.http_status, 422);
});
