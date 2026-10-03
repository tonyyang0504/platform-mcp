import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/kkj_go_jp.json", import.meta.url), "utf8"));
const resp = (status, text, ct) => ({ status, headers: { get: (k) => (k.toLowerCase() === "content-type" ? ct : null) }, text: async () => text });
const XML = '<?xml version="1.0" encoding="utf-8" ?><Results><Version>1.0</Version><SearchResults><SearchHits>2</SearchHits>'
  + '<SearchResult><ResultId>1</ResultId><Key><![CDATA[KEY1]]></Key><ExternalDocumentURI><![CDATA[https://www.city.example.lg.jp/a.pdf]]></ExternalDocumentURI>'
  + '<ProjectName>スタッドレスタイヤ購入</ProjectName><OrganizationName>福島県田村市</OrganizationName><CftIssueDate>2026-09-04T00:00:00+09:00</CftIssueDate>'
  + '<TenderSubmissionDeadline>2026-09-29T00:00:00+09:00</TenderSubmissionDeadline><Category>物品</Category></SearchResult></SearchResults></Results>';

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

test("kkj_go_jp: search parses the XML search result (main, wire)", async () => {
  const client = await connect(() => resp(200, XML, "text/xml; charset=UTF-8"));
  const res = await client.callTool({ name: "search_postings", arguments: { query: "タイヤ", limit: 5 } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  const p = res.structuredContent.postings;
  assert.equal(p.length, 1);  // a single <SearchResult> is still a list
  assert.equal(p[0].id, "KEY1"); assert.equal(p[0].title, "スタッドレスタイヤ購入"); assert.equal(p[0].buyer, "福島県田村市");
  assert.equal(p[0].url, "https://www.city.example.lg.jp/a.pdf"); assert.equal(p[0].deadline, "2026-09-29T00:00:00+09:00");
  const q = client.log[0].url.searchParams;
  assert.equal(client.log[0].url.href.split("?")[0], "https://www.kkj.go.jp/api/");
  assert.equal(q.get("Query"), "タイヤ"); assert.equal(q.get("Count"), "5");
  assert.match(q.get("CFT_Issue_Date"), /^\d{4}-\d{2}-\d{2}\/$/);
});

test("kkj_go_jp: tools and failures (wire)", async () => {
  const client = await connect(() => resp(503, "search disabled", "text/plain"));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name), ["search_postings"]);
  const res = await client.callTool({ name: "search_postings", arguments: { query: "工事" } });
  assert.equal(res.isError, true); assert.equal(res.structuredContent.error, "upstream_error");
});
