import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/nhs_jobs.json", import.meta.url), "utf8"));
const xmlFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/xml" : null) }, text: async () => r.text ?? "" }; };
const vac = (id, ref) => `<vacancyDetails><id>${id}</id><reference>${ref}</reference><title>Nurse</title><description>36 hours</description><employer>InHealth Group</employer><salary>Negotiable</salary><postDate>2026-09-18T14:04:51.8</postDate><url>https://beta.jobs.nhs.uk/candidate/jobadvert/${ref}</url><locations><location>Bridgwater, BA11 5LA</location></locations></vacancyDetails>`;
const doc = (...v) => `<?xml version='1.0' encoding='UTF-8'?><nhsJobs>${v.join("")}<totalPages>1</totalPages><totalResults>2</totalResults></nhsJobs>`;

async function connect(handler) {
  globalThis.fetch = xmlFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("nhs_jobs: keyless tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_posting", "search"]);
});

test("nhs_jobs: search parses the XML feed (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { text: doc(vac(1, "M0035-26-0449"), vac(2, "A3233-26-0001")) }; });
  const res = await client.callTool({ name: "search", arguments: { query: "nurse", page: 2, limit: 2 } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.deepEqual(res.structuredContent.postings.map((p) => p.id), ["M0035-26-0449", "A3233-26-0001"]);
  assert.equal(res.structuredContent.postings[0].company, "InHealth Group");
  assert.equal(seen.pathname, "/api/v1/search_xml");
  assert.equal(seen.searchParams.get("keyword"), "nurse");
  assert.equal(seen.searchParams.get("page"), "2");
});

test("nhs_jobs: single vacancy is still a list; get_posting uses jobReference (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { text: doc(vac(3, "X-1")) }; });
  const s = await client.callTool({ name: "search", arguments: { query: "porter" } });
  assert.deepEqual(s.structuredContent.postings.map((p) => p.id), ["X-1"]);
  const g = await client.callTool({ name: "get_posting", arguments: { id: "X-1" } });
  assert.equal(g.isError, false, JSON.stringify(g.structuredContent));
  assert.equal(g.structuredContent.title, "Nurse");
  assert.equal(seen.searchParams.get("jobReference"), "X-1");
});
