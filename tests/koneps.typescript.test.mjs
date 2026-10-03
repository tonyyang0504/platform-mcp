import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/koneps.json", import.meta.url), "utf8"));
const resp = (status, text, ct) => ({ status, headers: { get: (k) => (k.toLowerCase() === "content-type" ? ct : null) }, text: async () => text });
const ITEM = "<item><bidNtceNo>R25BK00933736</bidNtceNo><bidNtceOrd>000</bidNtceOrd><bidNtceDt>2025-07-01 09:28:14</bidNtceDt><bidNtceNm>AI 용역</bidNtceNm>"
  + "<dminsttNm>한국생산기술연구원</dminsttNm><bidClseDt>2025-07-15 10:00:00</bidClseDt><presmptPrce>46363636</presmptPrce>"
  + "<bidNtceDtlUrl>https://www.g2b.go.kr/link/PNPE027_01/single/?bidPbancNo=R25BK00933736&amp;bidPbancOrd=000</bidNtceDtlUrl></item>";
const XML = `<response><header><resultCode>00</resultCode><resultMsg>정상</resultMsg></header><body><items>${ITEM}</items><numOfRows>10</numOfRows><pageNo>1</pageNo><totalCount>1</totalCount></body></response>`;

async function connect(handler) {
  const log = [];
  const fetcher = async (url, init) => { log.push({ url: new URL(url), init }); return handler(); };
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { service_key: "KEY-abc123==" }, 50, "test", fetcher));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  client.log = log;
  return client;
}

test("koneps: search_postings sends the YYYYMMDDHHMM window and parses XML (main, wire)", async () => {
  const client = await connect(() => resp(200, XML, "application/xml"));
  const res = await client.callTool({ name: "search_postings", arguments: { query: "AI", min_budget: 5000000 } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  const p = res.structuredContent.postings;
  assert.equal(p.length, 1);
  assert.equal(p[0].id, "R25BK00933736"); assert.equal(p[0].buyer, "한국생산기술연구원"); assert.equal(p[0].currency, "KRW");
  assert.equal(p[0].url, "https://www.g2b.go.kr/link/PNPE027_01/single/?bidPbancNo=R25BK00933736&bidPbancOrd=000");
  const u = client.log[0].url; const q = u.searchParams;
  assert.equal(u.pathname, "/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch");
  assert.equal(q.get("serviceKey"), "KEY-abc123=="); assert.equal(q.get("inqryDiv"), "1"); assert.equal(q.get("bidNtceNm"), "AI");
  assert.equal(q.get("presmptPrceBgn"), "5000000"); assert.equal(q.get("bidClseExcpYn"), "Y");
  assert.match(q.get("inqryBgnDt"), /^\d{8}0000$/); assert.match(q.get("inqryEndDt"), /^\d{12}$/);
  const d30 = new Date(Date.now() - 30 * 86400000).toISOString().slice(0, 10).replaceAll("-", "");
  assert.equal(q.get("inqryBgnDt").slice(0, 8), d30);
});

test("koneps: get_posting by bidNtceNo (wire)", async () => {
  const client = await connect(() => resp(200, XML, "application/xml"));
  const res = await client.callTool({ name: "get_posting", arguments: { id: "R25BK00933736" } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.equal(res.structuredContent.title, "AI 용역");
  const q = client.log[0].url.searchParams;
  assert.equal(client.log[0].url.pathname.endsWith("/getBidPblancListInfoServc"), true);
  assert.equal(q.get("inqryDiv"), "2"); assert.equal(q.get("bidNtceNo"), "R25BK00933736");
});

test("koneps: rate limit is an isError result (wire)", async () => {
  const client = await connect(() => ({ status: 429, headers: { get: (k) => (k.toLowerCase() === "retry-after" ? "5" : null) }, text: async () => "" }));
  const res = await client.callTool({ name: "search_postings", arguments: {} });
  assert.equal(res.isError, true); assert.equal(res.structuredContent.error, "rate_limited");
});
