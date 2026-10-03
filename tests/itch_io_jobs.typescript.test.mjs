import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/itch_io_jobs.json", import.meta.url), "utf8"));
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
const FEED = "https://itch.io/board/10020/help-wanted-or-offered.rss";
const XML = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><rss version=\"2.0\"><channel><title>Feed</title><link>https://example.invalid/</link><item><guid>https://itch.io/t/6995248/paid-pixel-artist-wanted</guid><title>[PAID] Pixel artist wanted</title><link>https://itch.io/t/6995248/paid-pixel-artist-wanted</link><pubDate>Fri, 25 Sep 2026 03:32:52 GMT</pubDate><createDate>Fri, 25 Sep 2026 03:32:52 GMT</createDate><updateDate>Fri, 25 Sep 2026 03:36:44 GMT</updateDate><description><![CDATA[<p>Looking for a pixel artist.</p>]]></description></item><item><guid>https://itch.io/t/6995250/composer-for-hire</guid><title>Composer for hire</title><link>https://itch.io/t/6995250/composer-for-hire</link><pubDate>Fri, 25 Sep 2026 04:00:00 GMT</pubDate><description>Music</description></item></channel></rss>";

test("itch_io_jobs: only search_postings is offered (wire)", async () => {
  const client = await connect(() => resp(200, "", "text/plain"));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name), ["search_postings"]);
  assert.equal(tools[0].annotations.readOnlyHint, true);
});

test("itch_io_jobs: search_postings parses the RSS feed (main, wire)", async () => {
  const client = await connect(() => resp(200, XML, "application/rss+xml; charset=utf-8"));
  const res = await client.callTool({ name: "search_postings", arguments: {"query": "artist"} });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  const p = res.structuredContent.postings;
  assert.equal(p.length, 2);
  const expect = {"id": "https://itch.io/t/6995248/paid-pixel-artist-wanted", "title": "[PAID] Pixel artist wanted", "url": "https://itch.io/t/6995248/paid-pixel-artist-wanted", "posted_at": "Fri, 25 Sep 2026 03:32:52 GMT", "description": "<p>Looking for a pixel artist.</p>"};
  for (const [k, v] of Object.entries(expect)) assert.equal(p[0][k], v, k);
  assert.equal(p[0].raw["updateDate"], "Fri, 25 Sep 2026 03:36:44 GMT");
  const seen = client.log[0];
  assert.equal(seen.url.href.split("?")[0], FEED);
  assert.equal(seen.init.method, "GET");
  assert.deepEqual(Object.fromEntries(seen.url.searchParams), {});
});

test("itch_io_jobs: rate limit is an isError result (wire)", async () => {
  const client = await connect(() => resp(429, "", "text/plain", { "retry-after": "30" }));
  const res = await client.callTool({ name: "search_postings", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
});
