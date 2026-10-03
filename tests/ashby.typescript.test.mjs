import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/ashby.json", import.meta.url), "utf8"));
const JOB = { id: "7458d4e9-da2e-47bd-98cb-adfda43d42b2", title: "Engineering Manager - EU", location: "Remote - European Union", publishedAt: "2024-03-04T14:29:08.532+00:00", jobUrl: "https://jobs.ashbyhq.com/Ashby/7458d4e9-da2e-47bd-98cb-adfda43d42b2", descriptionPlain: "Hi", workplaceType: "Remote" };
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (typeof r.body === "string" ? r.body : JSON.stringify(r.body ?? {})) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { job_board_name: "Ashby" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("only search is offered (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name), ["search"]);
  assert.equal(tools[0].annotations.readOnlyHint, true);
  assert.equal(tools[0]._meta["platform_mcp/docs"], "https://developers.ashbyhq.com/docs/public-job-posting-api");
});

test("search reads the configured board with compensation and no query (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { apiVersion: "1", jobs: [JOB] } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "manager", location: "Berlin" } });
  assert.equal(res.isError, false);
  assert.equal(seen.origin + seen.pathname, "https://api.ashbyhq.com/posting-api/job-board/Ashby");
  assert.deepEqual([...seen.searchParams.entries()], [["includeCompensation", "true"]]);
  const p = res.structuredContent.postings[0];
  assert.equal(p.id, "7458d4e9-da2e-47bd-98cb-adfda43d42b2");
  assert.equal(p.location, "Remote - European Union");
  assert.equal(p.description, "Hi");
  assert.equal(res.structuredContent.next_page, null);
});

test("unknown board is invalid_input (wire)", async () => {
  const client = await connect(() => ({ status: 404, body: "Not Found" }));
  const res = await client.callTool({ name: "search", arguments: { query: "x" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "not_found");
});
