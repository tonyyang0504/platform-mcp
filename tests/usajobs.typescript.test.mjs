import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/usajobs.json", import.meta.url), "utf8"));
const ITEM = { MatchedObjectId: "812345600", MatchedObjectDescriptor: { PositionID: "DE-12345-26-ABC", PositionTitle: "IT Specialist (APPSW)", PositionURI: "https://www.usajobs.gov/job/812345600", ApplyURI: ["https://www.usajobs.gov/job/812345600?PostingChannelID=RESTAPI"], PositionLocation: [{ LocationName: "Washington, District of Columbia", CountryCode: "United States" }], PositionRemuneration: [{ MinimumRange: "99200.0", MaximumRange: "128956.0", RateIntervalCode: "PA" }], QualificationSummary: "You must have one year ...", UserArea: { Details: { JobSummary: "Serves as ..." } } } };
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_key: "k", email: "me@example.com" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("usajobs tools (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_posting", "me", "search"]);
});

test("usajobs search sends Authorization-Key + User-Agent e-mail and maps documented fields (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { SearchResult: { SearchResultCount: 1, SearchResultItems: [ITEM] } } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "python", location: "Washington, DC" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.postings[0].id, "DE-12345-26-ABC");
  assert.equal(res.structuredContent.postings[0].location, "Washington, District of Columbia");
  assert.equal(res.structuredContent.postings[0].url, "https://www.usajobs.gov/job/812345600");
  assert.equal(seen.init.headers["Authorization-Key"], "k");
  assert.equal(seen.init.headers["User-Agent"], "me@example.com");
  assert.equal(seen.url.searchParams.get("Keyword"), "python");
  assert.equal(seen.url.searchParams.get("ResultsPerPage"), "25");
  assert.equal(seen.url.searchParams.get("Page"), "1");
});

test("usajobs get_posting resolves the first search hit for a PositionID (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { SearchResult: { SearchResultCount: 1, SearchResultItems: [ITEM] } } }; });
  const res = await client.callTool({ name: "get_posting", arguments: { id: "DE-12345-26-ABC" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.title, "IT Specialist (APPSW)");
  assert.equal(seen.searchParams.get("PositionID"), "DE-12345-26-ABC");
});

test("usajobs 401 is an auth_error result (wire)", async () => {
  const res = await (await connect(() => ({ status: 401, body: {} }))).callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
});
