import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/talentlyft.json", import.meta.url), "utf8"));
const JOB = { Id: 20532, Title: "Creative Director", ShortlinkUrl: "https://demo.talentlyft.com/o/gRnagN", City: "Portland", Description: "<h2>Lead</h2>" };
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { subdomain: "demo" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("search pages with perPage and details=true (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { Results: [JOB], Count: 2 } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "director", page: 2, limit: 1 } });
  assert.equal(res.isError, false);
  assert.equal(seen.pathname, "/v2/public/demo/jobs");
  assert.equal(seen.searchParams.get("page"), "2");
  assert.equal(seen.searchParams.get("perPage"), "1");
  assert.equal(seen.searchParams.get("details"), "true");
  assert.equal(res.structuredContent.postings[0].id, "20532");
  assert.equal(res.structuredContent.total, 2);
});

test("unknown subdomain is invalid_input (wire)", async () => {
  const client = await connect(() => ({ status: 404, body: { Message: "Not Found" } }));
  const res = await client.callTool({ name: "search", arguments: { query: "x" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "not_found");
});
