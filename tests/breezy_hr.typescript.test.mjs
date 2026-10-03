import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/breezy_hr.json", import.meta.url), "utf8"));
const TOKEN = "breezy_pat_secret123456";
const POS = { _id: "a3f9c1d2e4b5", name: "Backend Engineer", location: { name: "Austin, TX" }, description: "<p>Build APIs</p>", creation_date: "2026-09-01T10:00:00.000Z", salary: { from: 120000, to: 150000, period: "year", currency: "USD" } };
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_token: TOKEN, company_id: "c0ffee123456" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_posting", "me", "search"]);
});

test("search sends bearer, state=published and capped page_size (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: [POS] }; });
  const res = await client.callTool({ name: "search", arguments: { query: "backend", page: 2, limit: 80 } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.pathname, "/v3/company/c0ffee123456/positions");
  assert.equal(seen.init.headers.Authorization, `Bearer ${TOKEN}`);
  assert.equal(seen.url.searchParams.get("state"), "published");
  assert.equal(seen.url.searchParams.get("page_size"), "50");
  assert.equal(seen.url.searchParams.get("page"), "2");
  const p = res.structuredContent.postings[0];
  assert.equal(p.id, "a3f9c1d2e4b5");
  assert.equal(p.salary_max, 150000);
});

test("403 is auth_error and the token is scrubbed (wire)", async () => {
  const client = await connect(() => ({ status: 403, body: { error: { type: "companyMembershipRequired", message: `token ${TOKEN}` } } }));
  const res = await client.callTool({ name: "search", arguments: { query: "x" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.ok(!JSON.stringify(res).includes(TOKEN));
});
