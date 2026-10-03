import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/himalayas.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const JOB = { title: "Senior React Native Developer", companyName: "lemon.io", currency: "USD", categories: ["React-Native-Developer"], excerpt: "…", applicationLink: "https://himalayas.app/companies/lemon-io/jobs/x", guid: "https://himalayas.app/companies/lemon-io/jobs/x" };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, {}, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("himalayas (deals): search hits /jobs/api/search with q and sort (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { totalCount: 1, jobs: [JOB] } }; });
  const res = await client.callTool({ name: "search_postings", arguments: { query: "react", category: "Contractor" } });
  assert.equal(res.isError, false);
  assert.equal(seen.origin + seen.pathname, "https://himalayas.app/jobs/api/search");
  assert.equal(seen.searchParams.get("q"), "react");
  assert.equal(seen.searchParams.get("employment_type"), "Contractor");
  assert.equal(seen.searchParams.get("sort"), "recent");
  assert.equal(seen.searchParams.get("limit"), null);
  assert.equal(res.structuredContent.postings[0].buyer, "lemon.io");
});
