import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/trademe_jobs.json", import.meta.url), "utf8"));
process.env.PLATFORM_MCP_TRADEME_JOBS_CONSUMER_KEY = "CK4E0D0823";
process.env.PLATFORM_MCP_TRADEME_JOBS_CONSUMER_SECRET = "CSEC160FCF";
process.env.PLATFORM_MCP_TRADEME_JOBS_OAUTH_TOKEN = "TOKFC68E514";
process.env.PLATFORM_MCP_TRADEME_JOBS_OAUTH_TOKEN_SECRET = "TSEC5333F6";
async function connect(handler) {
  globalThis.fetch = async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null) }, text: async () => JSON.stringify(r.body ?? {}) }; };
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("trademe_jobs: OAuth PLAINTEXT header and job search mapping (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { TotalCount: 1, List: [{ ListingId: 49, Title: "Dev", Company: "Kiwi Ltd", Region: "Wellington" }] } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "developer", page: 1, limit: 10 } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.equal(res.structuredContent.postings[0].id, "49");
  assert.equal(seen.url.pathname, "/v1/Search/Jobs.json");
  assert.deepEqual(Object.fromEntries(seen.url.searchParams), { search_string: "developer", page: "1", rows: "10" });
  assert.equal(seen.init.headers.Authorization ?? seen.init.headers.authorization,
    "OAuth oauth_consumer_key=CK4E0D0823, oauth_token=TOKFC68E514, oauth_signature_method=PLAINTEXT, oauth_signature=CSEC160FCF%26TSEC5333F6");
});
