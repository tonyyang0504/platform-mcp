import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/workable.json", import.meta.url), "utf8"));
const TOKEN = "wk_secret_token_4f7a9b";
const JOB = { id: "61884e2", title: "Sales Intern", shortcode: "GROOV003", url: "https://groove-tech.workable.com/jobs/102268944", location: { location_str: "Portland, Oregon, United States" }, salary: { salary_from: 10000, salary_to: 20000, salary_currency: "eur" }, created_at: "2015-07-01T00:00:00Z" };
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_token: TOKEN, subdomain: "groove-tech" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("search lists published jobs on the account host (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { jobs: [JOB] } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "sales", limit: 500 } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.origin + seen.url.pathname, "https://groove-tech.workable.com/spi/v3/jobs");
  assert.equal(seen.init.headers.Authorization, `Bearer ${TOKEN}`);
  assert.equal(seen.url.searchParams.get("limit"), "100");
  assert.equal(seen.url.searchParams.get("state"), "published");
  assert.equal(res.structuredContent.postings[0].id, "GROOV003");
});

test("me probes the account on workable.com (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { id: "20ff5c50", name: "Groove Tech" } }; });
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, false);
  assert.equal(seen.origin + seen.pathname, "https://workable.com/spi/v3/accounts/groove-tech");
  assert.equal(res.structuredContent.account.name, "Groove Tech");
});

test("401 is auth_error and scrubbed (wire)", async () => {
  const client = await connect(() => ({ status: 401, body: { error: `Not authorized: ${TOKEN}` } }));
  const res = await client.callTool({ name: "get_posting", arguments: { id: "GROOV003" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.ok(!JSON.stringify(res).includes(TOKEN));
});
