import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/market_data/news_collector.json", import.meta.url), "utf8"));
const json = (status, body) => ({ status, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null) }, text: async () => JSON.stringify(body) });

async function connect(handler) {
  const log = [];
  const fetcher = async (url, init) => { log.push({ url: new URL(url), init }); return handler(); };
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, {}, 50, "test", fetcher));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  client.log = log;
  return client;
}

test("news_collector: get_news maps GDELT ArtList (main, wire)", async () => {
  const client = await connect(() => json(200, { articles: [{ url: "https://x.example/a", title: "Oil jumps", seendate: "20260925T021500Z", domain: "x.example", language: "English" }] }));
  const res = await client.callTool({ name: "get_news", arguments: { query: "oil", since: "2026-09-20T06:30:00Z", limit: 10 } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  const a = res.structuredContent.articles[0];
  assert.equal(a.id, "https://x.example/a"); assert.equal(a.source, "x.example"); assert.equal(a.published_at, "20260925T021500Z");
  const q = client.log[0].url.searchParams;
  assert.equal(client.log[0].url.href.split("?")[0], "https://api.gdeltproject.org/api/v2/doc/doc");
  assert.equal(q.get("mode"), "artlist"); assert.equal(q.get("format"), "json"); assert.equal(q.get("maxrecords"), "10");
  assert.equal(q.get("startdatetime"), "20260920063000");
});

test("news_collector: tools and rate limit (wire)", async () => {
  const client = await connect(() => ({ status: 429, headers: { get: (k) => (k.toLowerCase() === "retry-after" ? "5" : null) }, text: async () => "" }));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name), ["get_news"]);
  const res = await client.callTool({ name: "get_news", arguments: { query: "oil" } });
  assert.equal(res.isError, true); assert.equal(res.structuredContent.error, "rate_limited");
});
