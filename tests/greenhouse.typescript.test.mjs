import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/greenhouse.json", import.meta.url), "utf8"));
const JOB = { id: 127817, title: "Vault Designer", location: { name: "NYC" }, absolute_url: "https://boards.greenhouse.io/vaulttec/jobs/127817", company_name: "Vault-Tec", first_published: "2016-01-10T09:00:00-05:00", content: "desc" };
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { board_token: "vaulttec" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_posting", "search"]);
  assert.ok(tools.every((t) => t.annotations.readOnlyHint === true));
});

test("search lists the configured board with content=true (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { jobs: [JOB], meta: { total: 1 } } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "designer" } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.pathname, "/v1/boards/vaulttec/jobs");
  assert.equal(seen.url.searchParams.get("content"), "true");
  assert.equal(seen.init.headers.Authorization, undefined);
  const p = res.structuredContent.postings[0];
  assert.equal(p.id, "127817");
  assert.equal(p.company, "Vault-Tec");
  assert.equal(p.location, "NYC");
  assert.equal(res.structuredContent.total, 1);
});

test("get_posting maps the first pay range (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { ...JOB, pay_input_ranges: [{ min_cents: 5000000, max_cents: 7500000, currency_type: "USD" }] } }; });
  const res = await client.callTool({ name: "get_posting", arguments: { id: "127817" } });
  assert.equal(res.isError, false);
  assert.equal(seen.pathname, "/v1/boards/vaulttec/jobs/127817");
  assert.equal(seen.searchParams.get("pay_transparency"), "true");
  assert.equal(res.structuredContent.salary_min, 5000000);
  assert.equal(res.structuredContent.currency, "USD");
});
