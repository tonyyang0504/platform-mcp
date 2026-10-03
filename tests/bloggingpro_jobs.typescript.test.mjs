import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/bloggingpro_jobs.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const ROW = { id: 36676, date_gmt: "2026-08-04T16:23:50", link: "https://www.bloggingpro.com/job/36676/discord-product-designer-growth/", title: { rendered: "Product Designer, Growth" }, content: { rendered: "<p>x</p>" }, meta: { _company_name: "Discord" } };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, {}, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("bloggingpro_jobs: search hits the WP REST job-listings route (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: [ROW] }; });
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_posting", "search_postings"]);
  const res = await client.callTool({ name: "search_postings", arguments: { query: "designer", category: "21", page: 2, limit: 5 } });
  assert.equal(res.isError, false);
  assert.equal(seen.origin + seen.pathname, "https://www.bloggingpro.com/wp-json/wp/v2/job-listings");
  assert.equal(seen.searchParams.get("search"), "designer");
  assert.equal(seen.searchParams.get("job-categories"), "21");
  assert.equal(seen.searchParams.get("per_page"), "5");
  const p = res.structuredContent.postings[0];
  assert.equal(p.id, "36676");
  assert.equal(p.title, "Product Designer, Growth");
  assert.equal(p.buyer, "Discord");
});

test("bloggingpro_jobs: unknown id is an isError result (wire)", async () => {
  const client = await connect(() => ({ status: 404, body: { code: "rest_post_invalid_id", message: "Invalid post ID." } }));
  const res = await client.callTool({ name: "get_posting", arguments: { id: "1" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "not_found");
});
