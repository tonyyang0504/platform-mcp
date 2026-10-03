import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/e_zamowienia.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const NOTICE = { noticeNumber: "2026/BZP 00438129/01", orderObject: "Zakup i dostawa autobusu", organizationName: "Gmina Chmielnik", publicationDate: "2026-09-15T09:10:55Z", submittingOffersDate: "2026-09-24T08:00:00Z" };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, {}, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("e_zamowienia: search sends the month window and filters (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: [NOTICE] }; });
  const res = await client.callTool({ name: "search_postings", arguments: { query: "autobus", limit: 10 } });
  assert.equal(res.isError, false);
  assert.equal(seen.origin + seen.pathname, "https://ezamowienia.gov.pl/mo-board/api/v1/notice");
  assert.equal(seen.searchParams.get("NoticeType"), "ContractNotice");
  assert.equal(seen.searchParams.get("OrderObject"), "autobus");
  assert.match(seen.searchParams.get("PublicationDateFrom"), /^\d{4}-\d{1,2}-01T00:00:00Z$/);
  assert.ok(seen.searchParams.get("PublicationDateTo"));
  assert.equal(res.structuredContent.postings[0].id, "2026/BZP 00438129/01");
});

test("e_zamowienia: get_posting reads the first array element; empty is isError (wire)", async () => {
  let n = 0;
  const client = await connect(() => ({ body: n++ === 0 ? [NOTICE] : [] }));
  const ok = await client.callTool({ name: "get_posting", arguments: { id: "2026/BZP 00438129/01" } });
  assert.equal(ok.structuredContent.buyer, "Gmina Chmielnik");
  const miss = await client.callTool({ name: "get_posting", arguments: { id: "x" } });
  assert.equal(miss.isError, true);
  assert.equal(miss.structuredContent.error, "not_found");
});
