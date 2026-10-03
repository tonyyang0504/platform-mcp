import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/fl_ru.json", import.meta.url), "utf8"));
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
const FEED = "https://www.fl.ru/rss/all.xml";
const XML = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><rss version=\"2.0\"><channel><title>Feed</title><link>https://example.invalid/</link><item><title><![CDATA[Сверстать лендинг]]></title><link>https://www.fl.ru/projects/5523294/sverstat-lending.html</link><description><![CDATA[Нужно сверстать лендинг по макету в Figma.]]></description><guid>https://www.fl.ru/projects/5523294/sverstat-lending.html</guid><category><![CDATA[Сайты / Верстка]]></category><pubDate>Fri, 25 Sep 2026 04:45:37 GMT</pubDate></item><item><title>Логотип для кофейни</title><link>https://www.fl.ru/projects/5523301/logotip.html</link><description>Нужен логотип</description><guid>https://www.fl.ru/projects/5523301/logotip.html</guid><category>Дизайн / Логотипы</category><pubDate>Fri, 25 Sep 2026 05:01:00 GMT</pubDate></item></channel></rss>";

test("fl_ru: only search_postings is offered (wire)", async () => {
  const client = await connect(() => resp(200, "", "text/plain"));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name), ["search_postings"]);
  assert.equal(tools[0].annotations.readOnlyHint, true);
});

test("fl_ru: search_postings parses the RSS feed (main, wire)", async () => {
  const client = await connect(() => resp(200, XML, "application/rss+xml; charset=utf-8"));
  const res = await client.callTool({ name: "search_postings", arguments: {"query": "лендинг", "page": 1} });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  const p = res.structuredContent.postings;
  assert.equal(p.length, 2);
  const expect = {"id": "https://www.fl.ru/projects/5523294/sverstat-lending.html", "title": "Сверстать лендинг", "url": "https://www.fl.ru/projects/5523294/sverstat-lending.html", "posted_at": "Fri, 25 Sep 2026 04:45:37 GMT", "description": "Нужно сверстать лендинг по макету в Figma."};
  for (const [k, v] of Object.entries(expect)) assert.equal(p[0][k], v, k);
  assert.equal(p[0].raw["category"], "Сайты / Верстка");
  const seen = client.log[0];
  assert.equal(seen.url.href.split("?")[0], FEED);
  assert.equal(seen.init.method, "GET");
  assert.deepEqual(Object.fromEntries(seen.url.searchParams), {});
});

test("fl_ru: rate limit is an isError result (wire)", async () => {
  const client = await connect(() => resp(429, "", "text/plain", { "retry-after": "30" }));
  const res = await client.callTool({ name: "search_postings", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
});
