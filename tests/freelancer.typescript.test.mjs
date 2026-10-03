import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/freelancer.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const dig = (o, p) => p.split(".").reduce((a, k) => (a == null ? a : a[k]), o);
process.env.PLATFORM_MCP_FREELANCER_ACCESS_TOKEN = "FL-TOKEN-secret";
process.env.PLATFORM_MCP_FREELANCER_BIDDER_ID = "4242";
process.env.PLATFORM_MCP_FREELANCER_MILESTONE_PERCENTAGE = "50";

async function connect(handler) {
  const tokens = [];
  globalThis.fetch = fakeFetch((url, init) => {
    return handler(url, init);
  });
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  client.tokens = tokens;
  return client;
}

test("freelancer: tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["bid_status", "get_posting", "list_messages", "me", "search_postings", "send_message", "submit_bid", "withdraw_bid"]);
  for (const t of tools) { assert.equal(t.inputSchema.additionalProperties, false); assert.ok(t.title); }
});

test("freelancer: submit_bid maps documented fields (main, wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 200, body: {"status": "success", "result": {"id": 9001, "bidder_id": 4242, "project_id": 101, "award_status": null}} }; });
  const res = await client.callTool({ name: "submit_bid", arguments: {"posting_id": "101", "amount": 250.5, "period_days": 7, "message": "Proposal"} });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.deepEqual(dig(res.structuredContent, "bid_id"), "9001");
  assert.deepEqual(dig(res.structuredContent, "status"), "submitted");
  assert.equal(seen.url.href.split("?")[0], "https://www.freelancer.com/api/projects/0.1/bids/");
  assert.equal(seen.init.method, "POST");
  assert.equal((seen.init.headers["freelancer-oauth-v1"] ?? seen.init.headers["freelancer-oauth-v1"]), "FL-TOKEN-secret");
  assert.deepEqual(JSON.parse(seen.init.body), {"project_id": 101, "bidder_id": 4242, "amount": 250.5, "period": 7, "milestone_percentage": 50, "description": "Proposal"});
});

test("freelancer: withdraw_bid maps documented fields (extra, wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 200, body: {"status": "success"} }; });
  const res = await client.callTool({ name: "withdraw_bid", arguments: {"bid_id": "9001"} });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.deepEqual(dig(res.structuredContent, "status"), "retracted");
  assert.equal(seen.url.href.split("?")[0], "https://www.freelancer.com/api/projects/0.1/bids/9001/");
  assert.equal(seen.init.method, "PUT");
  assert.deepEqual(Object.fromEntries(new URLSearchParams(seen.init.body)), {"action": "retract"});
});

test("freelancer: rate limit is an isError result (wire)", async () => {
  const client = await connect(() => ({ status: 429, headers: { "Retry-After": "30" } }));
  const res = await client.callTool({ name: "search_postings", arguments: {"query": "x"} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
  assert.equal(res.structuredContent.retry_after_seconds, 30);
});
