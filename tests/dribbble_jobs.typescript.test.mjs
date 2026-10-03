import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/dribbble_jobs.json", import.meta.url), "utf8"));
const TWO = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><rss version=\"2.0\" xmlns:content=\"http://purl.org/rss/1.0/modules/content/\" xmlns:dc=\"http://purl.org/dc/elements/1.1/\" xmlns:job_listing=\"https://example.invalid/job_listing\" xmlns:wfw=\"http://wellformedweb.org/CommentAPI/\"><channel><title>Feed</title><link>https://example.invalid/</link><item><title>Designer at Acme</title><link>https://dribbble.com/jobs/designer-1</link><description>We are hiring</description><pubDate>Thu, 24 Sep 2026 08:06:00 GMT</pubDate><guid>https://dribbble.com/jobs/designer-1</guid><dc:creator>Millie</dc:creator></item><item><title>Designer at Acme</title><link>https://dribbble.com/jobs/designer-19</link><description>We are hiring</description><pubDate>Thu, 24 Sep 2026 08:06:00 GMT</pubDate><guid>https://dribbble.com/jobs/designer-19</guid><dc:creator>Millie</dc:creator></item></channel></rss>";
const EXPECTED = {"id": "https://dribbble.com/jobs/designer-1", "title": "Designer at Acme", "url": "https://dribbble.com/jobs/designer-1", "posted_at": "Thu, 24 Sep 2026 08:06:00 GMT", "description": "We are hiring", "company": "Millie"};
const QUERY = {"keyword": "design"};
const xmlFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/rss+xml" : null) }, text: async () => r.text ?? "" }; };

async function connect(handler) {
  globalThis.fetch = xmlFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("dribbble_jobs: only the keyless feed search is offered (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name), ["search"]);
});

test("dribbble_jobs: search parses the RSS feed and sends the documented parameters (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { text: TWO }; });
  const res = await client.callTool({ name: "search", arguments: {"query": "design", "location": "Leeds", "page": 2, "limit": 5} });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  const posts = res.structuredContent.postings;
  assert.equal(posts.length, 2);
  for (const [k, v] of Object.entries(EXPECTED)) assert.deepEqual(posts[0][k] ?? null, v, k);
  assert.equal(seen.origin + seen.pathname, "https://dribbble.com/jobs.rss");
  assert.deepEqual(Object.fromEntries(seen.searchParams), QUERY);
});
