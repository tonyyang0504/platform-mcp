import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/working_nomads.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, {}, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("working_nomads: only search is offered (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name), ["search"]);
});

test("working_nomads: search maps the keyless feed and sends no parameters (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: [{ url: "https://www.workingnomads.com/job/go/1/", title: "Dev", company_name: "Acme", location: "Europe", pub_date: "2026-09-20T10:00:00-04:00" }] }; });
  const res = await client.callTool({ name: "search", arguments: { query: "python", page: 2 } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.equal(res.structuredContent.postings[0].id, "https://www.workingnomads.com/job/go/1/");
  assert.equal(res.structuredContent.postings[0].company, "Acme");
  assert.equal(seen.pathname, "/api/exposed_jobs/");
  assert.equal([...seen.searchParams.keys()].length, 0);
});

test("working_nomads: 429 is rate_limited (wire)", async () => {
  const client = await connect(() => ({ status: 429, headers: { "Retry-After": "5" } }));
  const res = await client.callTool({ name: "search", arguments: { query: "x" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
});
