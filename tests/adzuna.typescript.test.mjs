import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/adzuna.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { app_id: "ID", app_key: "KEY" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("adzuna offers search + probe only (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["me", "search"]);
  assert.equal(tools.find((t) => t.name === "search")._meta["platform_mcp/endpoint"], "/jobs/{country}/search/{page}");
});

test("adzuna search sends app_id + app_key and fills the country/page path segments (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { results: [{ id: "4567890123", title: "Python Developer", description: "...", created: "2026-09-01T10:15:00Z", company: { display_name: "Acme Ltd" }, location: { area: ["UK", "London"], display_name: "London, UK" }, salary_min: 50000, salary_max: 60000, salary_is_predicted: "0", category: { tag: "it-jobs", label: "IT Jobs" }, contract_type: "permanent", redirect_url: "https://www.adzuna.co.uk/jobs/land/ad/4567890123" }], count: 1, mean: 55000 } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "python", location: "London", page: 2 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.postings[0].id, "4567890123");
  assert.equal(res.structuredContent.postings[0].company, "Acme Ltd");
  assert.equal(res.structuredContent.postings[0].location, "London, UK");
  assert.equal(res.structuredContent.total, 1);
  assert.equal(seen.url.pathname, "/v1/api/jobs/gb/search/2");
  assert.equal(seen.url.searchParams.get("what"), "python");
  assert.equal(seen.url.searchParams.get("where"), "London");
  assert.equal(seen.url.searchParams.get("results_per_page"), "25");
  assert.equal(seen.url.searchParams.get("app_id"), "ID");
  assert.equal(seen.url.searchParams.get("app_key"), "KEY");
  assert.equal(seen.init.headers.Authorization, undefined);
});

test("adzuna refused credentials are an isError result (wire)", async () => {
  const client = await connect(() => ({ status: 401, body: { exception: "AUTH_FAIL" } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.equal(res.structuredContent.http_status, 401);
});
