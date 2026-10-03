import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/recruitee.json", import.meta.url), "utf8"));
const TOKEN = "rc_careers_token_abc123";
const OFFER = { company_name: "Example company name", title: "Example offer 1", id: 1853589, slug: "example-offer-1", careers_url: "https://recruiteedemo.recruitee.com/o/example-offer-1", locations: [{ name: "Example location 1" }] };
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const creds = { careers_token: TOKEN, company_subdomain: "recruiteedemo", applicant_name: "John Smith", applicant_email: "john@example.com" };
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("search sends the careers token (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { offers: [OFFER] } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "x" } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.origin + seen.url.pathname, "https://recruiteedemo.recruitee.com/api/offers/");
  assert.equal(seen.init.headers["X-Careers-Sites-Token"], TOKEN);
  assert.equal(res.structuredContent.postings[0].id, "example-offer-1");
});

test("apply posts the nested candidate body (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 201, body: { candidate: { id: 7929046 } } }; });
  const res = await client.callTool({ name: "apply", arguments: { id: "example-offer-1", cover_letter: "Hello", resume_url: "https://example.com/CV.pdf" } });
  assert.equal(res.isError, false);
  assert.equal(seen.init.method, "POST");
  assert.equal(seen.url.pathname, "/api/offers/example-offer-1/candidates");
  assert.deepEqual(JSON.parse(seen.init.body), { candidate: { name: "John Smith", email: "john@example.com", cover_letter: "Hello", remote_cv_url: "https://example.com/CV.pdf" } });
  assert.equal(res.structuredContent.application_id, "7929046");
  assert.equal(res.structuredContent.status, "submitted");
});

test("refused application is isError and scrubbed (wire)", async () => {
  const client = await connect(() => ({ status: 422, body: { error: ["Phone can't be blank"], token: TOKEN } }));
  const res = await client.callTool({ name: "apply", arguments: { id: "example-offer-1" } });
  assert.equal(res.isError, true);
  assert.ok(!JSON.stringify(res).includes(TOKEN));
});
