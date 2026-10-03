import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/idealist.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const hdr = (init, name) => { const h = init.headers ?? {}; const k = Object.keys(h).find((x) => x.toLowerCase() === name.toLowerCase()); return k ? h[k] : undefined; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_key: "k1" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("idealist: tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_posting", "me", "search"]);
});

test("idealist: search sends Basic auth and the since cursor (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { jobs: [{ id: "job1", name: "Role 1", firstPublished: "2019-06-23T18:02:07Z", updated: "2019-06-23T18:02:08Z", url: { en: "https://www.idealist.org/en/nonprofit-job/1" } }], hasMore: false } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "director", cursor: "2019-06-01T00:00:00Z" } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.equal(res.structuredContent.postings[0].title, "Role 1");
  assert.equal(res.structuredContent.postings[0].url, "https://www.idealist.org/en/nonprofit-job/1");
  assert.equal(seen.url.pathname, "/api/v1/listings/jobs");
  assert.equal(seen.url.searchParams.get("since"), "2019-06-01T00:00:00Z");
  assert.equal(seen.url.searchParams.get("query"), null);
  assert.equal(hdr(seen.init, "Authorization"), "Basic " + Buffer.from("k1:").toString("base64"));
});

test("idealist: get_posting maps job details (wire)", async () => {
  const client = await connect(() => ({ body: { job: { id: "f976", name: "Executive Director", org: { name: "Example Organization" }, address: { full: "123 Broadway" }, url: { en: "https://x/f976" } } } }));
  const res = await client.callTool({ name: "get_posting", arguments: { id: "f976" } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.equal(res.structuredContent.company, "Example Organization");
  assert.equal(res.structuredContent.location, "123 Broadway");
});

test("idealist: 401 is an auth_error (wire)", async () => {
  const client = await connect(() => ({ status: 401, body: { detail: "check your API key" } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
});
