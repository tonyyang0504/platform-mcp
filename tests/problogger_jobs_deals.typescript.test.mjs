import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/problogger_jobs.json", import.meta.url), "utf8"));
const resp = (status, text, ct, extra = {}) => ({ status, headers: { get: (k) => ({ "content-type": ct, ...extra })[k.toLowerCase()] ?? null }, text: async () => text });

async function connect(handler, creds = {}) {
  const log = [];
  const fetcher = async (url, init) => { log.push({ url: new URL(url), init }); return handler(new URL(url), init); };
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fetcher));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  client.log = log;
  return client;
}
const FEED = "https://problogger.com/jobs/wpjobboard/xml/rss/";
const XML = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><rss version=\"2.0\"><channel><title>Feed</title><link>https://example.invalid/</link><item><title>Freelance Blog Writer</title><link>https://problogger.com/jobs/job/freelance-blog-writer-123/</link><pubDate>Wed, 23 Sep 2026 10:00:00 +0000</pubDate><guid isPermaLink=\"false\">https://problogger.com/jobs/?post_type=job_listing&amp;p=123</guid><description>Write 4 posts a month.</description></item><item><title>Editor</title><link>https://problogger.com/jobs/job/editor-124/</link><pubDate>Tue, 22 Sep 2026 10:00:00 +0000</pubDate><description>Edit.</description></item></channel></rss>";

test("problogger_jobs: only search_postings is offered (wire)", async () => {
  const client = await connect(() => resp(200, "", "text/plain"));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name), ["search_postings"]);
  assert.equal(tools[0].annotations.readOnlyHint, true);
});

test("problogger_jobs: search_postings parses the RSS feed (main, wire)", async () => {
  const client = await connect(() => resp(200, XML, "application/rss+xml; charset=utf-8"));
  const res = await client.callTool({ name: "search_postings", arguments: { query: "writer" } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  const p = res.structuredContent.postings;
  assert.equal(p.length, 2);
  const expect = {"id": "https://problogger.com/jobs/job/freelance-blog-writer-123/", "title": "Freelance Blog Writer", "url": "https://problogger.com/jobs/job/freelance-blog-writer-123/", "posted_at": "Wed, 23 Sep 2026 10:00:00 +0000", "description": "Write 4 posts a month."};
  for (const [k, v] of Object.entries(expect)) assert.equal(p[0][k], v, k);
  const seen = client.log[0];
  assert.equal(seen.url.href.split("?")[0], FEED);
  assert.equal(seen.init.method, "GET");
  assert.deepEqual(Object.fromEntries(seen.url.searchParams), { query: "writer", filter: "active" });
});

test("problogger_jobs: rate limit is an isError result (wire)", async () => {
  const client = await connect(() => resp(429, "", "text/plain", { "retry-after": "30" }));
  const res = await client.callTool({ name: "search_postings", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
});
