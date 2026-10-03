import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/work_with_indies.json", import.meta.url), "utf8"));
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
const FEED = "https://www.workwithindies.com/careers/rss.xml";
const XML = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><rss version=\"2.0\"><channel><title>Feed</title><link>https://example.invalid/</link><item><title>AstroNomad Studios is hiring a Senior Systems Game Designer to work from North America</title><link>https://www.workwithindies.com/careers/astronomad-studios-senior-systems-game-designer</link><guid>https://www.workwithindies.com/careers/astronomad-studios-senior-systems-game-designer</guid><description>Help architect gameplay systems. Tags: [Design] [Full Time]</description><pubDate>Fri, 25 Sep 2026 00:00:00 GMT</pubDate></item><item><title>Studio B is hiring a Producer</title><link>https://www.workwithindies.com/careers/studio-b-producer</link><guid>https://www.workwithindies.com/careers/studio-b-producer</guid><description>Produce. Tags: [Production]</description><pubDate>Thu, 24 Sep 2026 00:00:00 GMT</pubDate></item></channel></rss>";

test("work_with_indies: only search_postings is offered (wire)", async () => {
  const client = await connect(() => resp(200, "", "text/plain"));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name), ["search_postings"]);
  assert.equal(tools[0].annotations.readOnlyHint, true);
});

test("work_with_indies: search_postings parses the RSS feed (main, wire)", async () => {
  const client = await connect(() => resp(200, XML, "application/rss+xml; charset=utf-8"));
  const res = await client.callTool({ name: "search_postings", arguments: {"query": "designer"} });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  const p = res.structuredContent.postings;
  assert.equal(p.length, 2);
  const expect = {"id": "https://www.workwithindies.com/careers/astronomad-studios-senior-systems-game-designer", "title": "AstroNomad Studios is hiring a Senior Systems Game Designer to work from North America", "url": "https://www.workwithindies.com/careers/astronomad-studios-senior-systems-game-designer", "posted_at": "Fri, 25 Sep 2026 00:00:00 GMT", "description": "Help architect gameplay systems. Tags: [Design] [Full Time]"};
  for (const [k, v] of Object.entries(expect)) assert.equal(p[0][k], v, k);
  const seen = client.log[0];
  assert.equal(seen.url.href.split("?")[0], FEED);
  assert.equal(seen.init.method, "GET");
  assert.deepEqual(Object.fromEntries(seen.url.searchParams), {});
});

test("work_with_indies: rate limit is an isError result (wire)", async () => {
  const client = await connect(() => resp(429, "", "text/plain", { "retry-after": "30" }));
  const res = await client.callTool({ name: "search_postings", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
});
