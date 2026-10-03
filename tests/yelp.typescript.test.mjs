import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/yelp.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => (r.body === undefined ? "" : JSON.stringify(r.body)) }; };

process.env.PLATFORM_MCP_YELP_USERNAME = "partner-user";
process.env.PLATFORM_MCP_YELP_PASSWORD = "PASSWORDsecret1";

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("yelp: program list with offset, status map and basic auth (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { total: 1, payment_programs: [{ program_id: "hTF5", program_type: "CPC", program_status: "ACTIVE", start_date: "2015-12-10", program_metrics: { budget: 10000, currency: "USD" } }] } }; });
  const res = await client.callTool({ name: "list_campaigns", arguments: { account_id: "x", status: "current", page: 3, limit: 10 } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.pathname, "/programs/v1");
  assert.equal(seen.url.searchParams.get("offset"), "20");
  assert.equal(seen.url.searchParams.get("limit"), "10");
  assert.equal(seen.url.searchParams.get("program_status"), "CURRENT");
  assert.equal(seen.init.headers.Authorization, "Basic " + Buffer.from("partner-user:PASSWORDsecret1").toString("base64"));
  assert.equal(res.structuredContent.campaigns[0].budget, 10000);
});

test("yelp: resume posts to /program/{id}/resume/v1 (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 202 }; });
  const res = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "c6HT44", action: "resume" } });
  assert.equal(res.isError, false);
  assert.equal(seen.init.method, "POST");
  assert.equal(seen.url.pathname, "/program/c6HT44/resume/v1");
  assert.equal(res.structuredContent.status, "accepted");
});
