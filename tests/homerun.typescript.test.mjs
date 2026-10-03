import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/homerun.json", import.meta.url), "utf8"));
const KEY = "hr_live_secretkey987";
const VAC = { id: "job_SnhUsAg1QwTRFIRNUfM6", title: "Product Designer", description: "Design things", location: { name: "Amsterdam HQ" }, created_at: "2026-09-20T10:00:00Z" };
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_key: KEY }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("search keeps the literal filter/include and adds paging (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { data: [VAC] } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "designer", page: 3, limit: 20 } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.pathname, "/v2/vacancies");
  assert.equal(seen.init.headers.Authorization, `Bearer ${KEY}`);
  assert.equal(seen.url.searchParams.get("filter[status]"), "public");
  assert.deepEqual(seen.url.searchParams.getAll("include[]"), ["location", "department", "salaryIndication"]);
  assert.equal(seen.url.searchParams.get("page"), "3");
  assert.equal(seen.url.searchParams.get("perPage"), "20");
  assert.equal(res.structuredContent.postings[0].id, "job_SnhUsAg1QwTRFIRNUfM6");
});

test("get_posting unwraps data (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { data: VAC } }; });
  const res = await client.callTool({ name: "get_posting", arguments: { id: "job_SnhUsAg1QwTRFIRNUfM6" } });
  assert.equal(res.isError, false);
  assert.equal(seen.pathname, "/v2/vacancies/job_SnhUsAg1QwTRFIRNUfM6");
  assert.equal(res.structuredContent.location, "Amsterdam HQ");
});

test("401 is auth_error and the key is scrubbed (wire)", async () => {
  const client = await connect(() => ({ status: 401, body: { message: `Invalid key ${KEY}` } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.ok(!JSON.stringify(res).includes(KEY));
});
