import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/smartrecruiters.json", import.meta.url), "utf8"));
const ROW = { id: "744000148454651", name: "Data Operations Consultant", company: { name: "SmartRecruiters Inc" }, releasedDate: "2026-09-09T09:43:26.403Z", location: { fullLocation: "Krakow, Poland" } };
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { company_identifier: "smartrecruiters" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("search maps q, city, country, limit and offset (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { totalFound: 57, content: [ROW] } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "data", location: "Krakow", country: "pl", page: 3, limit: 10 } });
  assert.equal(res.isError, false);
  assert.equal(seen.pathname, "/v1/companies/smartrecruiters/postings");
  assert.equal(seen.searchParams.get("q"), "data");
  assert.equal(seen.searchParams.get("city"), "Krakow");
  assert.equal(seen.searchParams.get("offset"), "20");
  assert.equal(res.structuredContent.total, 57);
  assert.equal(res.structuredContent.postings[0].company, "SmartRecruiters Inc");
});

test("get_posting reads the job-ad description (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { ...ROW, postingUrl: "https://jobs.smartrecruiters.com/x", jobAd: { sections: { jobDescription: { text: "<p>Do</p>" } } } } }; });
  const res = await client.callTool({ name: "get_posting", arguments: { id: "744000148454651" } });
  assert.equal(res.isError, false);
  assert.equal(seen.pathname, "/v1/companies/smartrecruiters/postings/744000148454651");
  assert.equal(res.structuredContent.description, "<p>Do</p>");
});

test("429 is rate_limited (wire)", async () => {
  const client = await connect(() => ({ status: 429, headers: { "Retry-After": "3" } }));
  const res = await client.callTool({ name: "search", arguments: { query: "x" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
});
