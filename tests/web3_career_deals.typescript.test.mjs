import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/web3_career.json", import.meta.url), "utf8"));
const TOKEN = "w3c-token-abcdef0123456789";
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const JOB = { id: "abc123", title: "Senior Smart Contract Engineer", company: "ExampleDAO", tags: ["solidity"], apply_url: "https://web3.career/x?ref=abc", postedAt: "2025-03-15" };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { token: TOKEN }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("web3_career (deals): token and tag in the query, jobs from element 2 (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: ["ok", "v1", [JOB]] }; });
  const res = await client.callTool({ name: "search_postings", arguments: { category: "solidity", limit: 5 } });
  assert.equal(res.isError, false);
  assert.equal(seen.origin + seen.pathname, "https://web3.career/api/v1");
  assert.equal(seen.searchParams.get("token"), TOKEN);
  assert.equal(seen.searchParams.get("tag"), "solidity");
  assert.equal(res.structuredContent.postings[0].buyer, "ExampleDAO");
});

test("web3_career (deals): 401 is auth_error and the token is scrubbed (wire)", async () => {
  const client = await connect(() => ({ status: 401, body: { error: `invalid token ${TOKEN}` } }));
  const res = await client.callTool({ name: "search_postings", arguments: { category: "rust" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.ok(!JSON.stringify(res).includes(TOKEN));
});
