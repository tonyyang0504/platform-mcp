import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/service_bund_de.json", import.meta.url), "utf8"));
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
const FEED = "https://www.service.bund.de/Content/DE/Ausschreibungen/Suche/Formular.html";
const XML = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><rss version=\"2.0\"><channel><title>Feed</title><link>https://example.invalid/</link><item><title>Software für die Friedhofsverwaltung</title><link>https://www.service.bund.de/IMPORTE/Ausschreibungen/editor/Stadt-X/2026/09/6649990.html#track=feed-callforbids</link><description><![CDATA[Erfüllungsort: <strong>Leipzig</strong><br />Vergabestelle: <strong>Stadt Leipzig</strong><br />Angebotsfrist: <strong>13.10.2026 10:00</strong>]]></description><pubDate>Fri, 25 Sep 2026 07:00:00 +0200</pubDate><guid>https://www.service.bund.de/IMPORTE/Ausschreibungen/editor/Stadt-X/2026/09/6649990.html</guid></item><item><title>Reinigung</title><link>https://www.service.bund.de/IMPORTE/Ausschreibungen/a.html</link><description>x</description><pubDate>Thu, 24 Sep 2026 07:00:00 +0200</pubDate><guid>https://www.service.bund.de/IMPORTE/Ausschreibungen/a.html</guid></item></channel></rss>";

test("service_bund_de: only search_postings is offered (wire)", async () => {
  const client = await connect(() => resp(200, "", "text/plain"));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name), ["search_postings"]);
  assert.equal(tools[0].annotations.readOnlyHint, true);
});

test("service_bund_de: search_postings parses the RSS feed (main, wire)", async () => {
  const client = await connect(() => resp(200, XML, "application/rss+xml; charset=utf-8"));
  const res = await client.callTool({ name: "search_postings", arguments: {"query": "Software", "page": 1} });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  const p = res.structuredContent.postings;
  assert.equal(p.length, 2);
  const expect = {"id": "https://www.service.bund.de/IMPORTE/Ausschreibungen/editor/Stadt-X/2026/09/6649990.html", "title": "Software für die Friedhofsverwaltung", "url": "https://www.service.bund.de/IMPORTE/Ausschreibungen/editor/Stadt-X/2026/09/6649990.html#track=feed-callforbids", "posted_at": "Fri, 25 Sep 2026 07:00:00 +0200"};
  for (const [k, v] of Object.entries(expect)) assert.equal(p[0][k], v, k);
  const seen = client.log[0];
  assert.equal(seen.url.href.split("?")[0], FEED);
  assert.equal(seen.init.method, "GET");
  assert.deepEqual(Object.fromEntries(seen.url.searchParams), {"templateQueryString": "Software", "nn": "4641482", "resultsPerPage": "100", "sortOrder": "dateOfIssue_dt desc", "jobsrss": "true"});
});

test("service_bund_de: rate limit is an isError result (wire)", async () => {
  const client = await connect(() => resp(429, "", "text/plain", { "retry-after": "30" }));
  const res = await client.callTool({ name: "search_postings", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
});
