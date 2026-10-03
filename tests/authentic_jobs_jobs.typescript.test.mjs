import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/authentic_jobs.json", import.meta.url), "utf8"));
const ROW = { id: 36676, date_gmt: "2026-08-04T16:23:50", link: "https://authenticjobs.com/job/36676/product-designer/", title: { rendered: "Product Designer, Growth" }, content: { rendered: "<p>x</p>" }, meta: { _company_name: "Discord" } };
async function connect(handler) {
  globalThis.fetch = async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null) }, text: async () => JSON.stringify(r.body ?? {}) }; };
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("authentic_jobs (jobs): search and get_posting use the WP REST job-listings route (wire)", async () => {
  const seen = [];
  const client = await connect((url) => { seen.push(url); return { body: url.pathname.endsWith("/job-listings") ? [ROW] : ROW }; });
  const s = await client.callTool({ name: "search", arguments: { query: "designer", page: 2, limit: 5 } });
  assert.equal(s.isError, false, JSON.stringify(s.structuredContent));
  assert.equal(s.structuredContent.postings[0].company, "Discord");
  assert.equal(seen[0].pathname, "/wp-json/wp/v2/job-listings");
  assert.deepEqual(Object.fromEntries(seen[0].searchParams), { search: "designer", page: "2", per_page: "5" });
  const g = await client.callTool({ name: "get_posting", arguments: { id: "36676" } });
  assert.equal(g.structuredContent.title, "Product Designer, Growth");
  assert.equal(seen[1].pathname, "/wp-json/wp/v2/job-listings/36676");
});
