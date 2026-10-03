import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/lever.json", import.meta.url), "utf8"));
const POST = { id: "681fbc53", text: "Approved Professional 3", categories: { location: "Baltimore, MD" }, descriptionPlain: "Welcome", hostedUrl: "https://jobs.lever.co/leverdemo/681fbc53", salaryRange: { currency: "USD", min: 90000, max: 110000 } };
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler, host = "api.lever.co") {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { site: "leverdemo", api_host: host }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("search maps skip, limit, location and mode=json (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: [POST] }; });
  const res = await client.callTool({ name: "search", arguments: { query: "ops", location: "Baltimore, MD", page: 3, limit: 10 } });
  assert.equal(res.isError, false);
  assert.equal(seen.origin + seen.pathname, "https://api.lever.co/v0/postings/leverdemo");
  assert.equal(seen.searchParams.get("mode"), "json");
  assert.equal(seen.searchParams.get("skip"), "20");
  assert.equal(seen.searchParams.get("limit"), "10");
  assert.equal(seen.searchParams.get("location"), "Baltimore, MD");
  const p = res.structuredContent.postings[0];
  assert.equal(p.title, "Approved Professional 3");
  assert.equal(p.salary_min, 90000);
});

test("EU host and get_posting (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: POST }; }, "api.eu.lever.co");
  const res = await client.callTool({ name: "get_posting", arguments: { id: "681fbc53" } });
  assert.equal(res.isError, false);
  assert.equal(seen.origin + seen.pathname, "https://api.eu.lever.co/v0/postings/leverdemo/681fbc53");
  assert.equal(res.structuredContent.location, "Baltimore, MD");
});

test("unknown posting is invalid_input (wire)", async () => {
  const client = await connect(() => ({ status: 404, body: { ok: false, error: "Document not found" } }));
  const res = await client.callTool({ name: "get_posting", arguments: { id: "nope" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "not_found");
});
