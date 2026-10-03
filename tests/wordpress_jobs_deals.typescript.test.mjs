import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/wordpress_jobs.json", import.meta.url), "utf8"));
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
const FEED = "https://jobs.wordpress.net/feed/";
const XML = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><rss version=\"2.0\" xmlns:content=\"http://purl.org/rss/1.0/modules/content/\" xmlns:dc=\"http://purl.org/dc/elements/1.1/\"><channel><title>Feed</title><link>https://example.invalid/</link><item><title>WordPress Developer</title><link>https://jobs.wordpress.net/job/wordpress-developer-892/</link><dc:creator><![CDATA[jobposter]]></dc:creator><pubDate>Sun, 20 Sep 2026 07:23:06 +0000</pubDate><guid isPermaLink=\"false\">https://jobs.wordpress.net/?post_type=job&amp;p=64856</guid><description><![CDATA[We are looking for a WordPress developer [...]]]></description><content:encoded><![CDATA[<p>We are looking for a WordPress developer to build client sites.</p>]]></content:encoded></item><item><title>Plugin fix</title><link>https://jobs.wordpress.net/job/plugin-fix-1/</link><pubDate>Sat, 19 Sep 2026 07:00:00 +0000</pubDate><description>Fix a plugin</description><content:encoded>Fix a plugin</content:encoded></item></channel></rss>";

test("wordpress_jobs: only search_postings is offered (wire)", async () => {
  const client = await connect(() => resp(200, "", "text/plain"));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name), ["search_postings"]);
  assert.equal(tools[0].annotations.readOnlyHint, true);
});

test("wordpress_jobs: search_postings parses the RSS feed (main, wire)", async () => {
  const client = await connect(() => resp(200, XML, "application/rss+xml; charset=utf-8"));
  const res = await client.callTool({ name: "search_postings", arguments: {} });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  const p = res.structuredContent.postings;
  assert.equal(p.length, 2);
  const expect = {"id": "https://jobs.wordpress.net/job/wordpress-developer-892/", "title": "WordPress Developer", "url": "https://jobs.wordpress.net/job/wordpress-developer-892/", "posted_at": "Sun, 20 Sep 2026 07:23:06 +0000", "description": "<p>We are looking for a WordPress developer to build client sites.</p>"};
  for (const [k, v] of Object.entries(expect)) assert.equal(p[0][k], v, k);
  assert.equal(p[0].raw["creator"], "jobposter");
  const seen = client.log[0];
  assert.equal(seen.url.href.split("?")[0], FEED);
  assert.equal(seen.init.method, "GET");
  assert.deepEqual(Object.fromEntries(seen.url.searchParams), {});
});

test("wordpress_jobs: rate limit is an isError result (wire)", async () => {
  const client = await connect(() => resp(429, "", "text/plain", { "retry-after": "30" }));
  const res = await client.callTool({ name: "search_postings", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
});
