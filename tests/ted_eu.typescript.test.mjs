import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/ted_eu.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

const NOTICE = {
  "publication-number": "412169-2016", "publication-date": "2016-11-23+01:00",
  "notice-title": { eng: "Software licences and support", spa: "Licencias de software y soporte" },
  "buyer-name": { eng: ["Achilles South Europe, S.L.U."] },
  "deadline-receipt-tender-date-lot": ["2026-12-01+01:00"],
  links: { html: { ENG: "https://ted.europa.eu/en/notice/-/detail/412169-2016" } },
};

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, {}, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("ted_eu: only search_postings is offered (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name), ["search_postings"]);
  assert.equal(tools[0].annotations.readOnlyHint, true);
  assert.equal(tools[0]._meta["platform_mcp/endpoint"], "/v3/notices/search");
});

test("ted_eu: search posts a typed fields array with the expert query and maps i18n notices (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { notices: [NOTICE], totalNoticeCount: 43059 } }; });
  const res = await client.callTool({ name: "search_postings", arguments: { query: 'FT~"software"', page: 2, limit: 50 } });
  assert.equal(res.isError, false);
  const p = res.structuredContent.postings[0];
  assert.equal(p.id, "412169-2016");
  assert.equal(p.title, "Software licences and support");
  assert.equal(p.buyer, "Achilles South Europe, S.L.U.");
  assert.equal(p.url, "https://ted.europa.eu/en/notice/-/detail/412169-2016");
  assert.equal(p.deadline, "2026-12-01+01:00");
  assert.equal(res.structuredContent.total, 43059);
  assert.equal(seen.url.href, "https://api.ted.europa.eu/v3/notices/search");
  assert.equal(seen.init.method, "POST");
  assert.deepEqual(JSON.parse(seen.init.body), {
    query: 'FT~"software"', fields: ["publication-number", "notice-title", "publication-date", "buyer-name", "deadline-receipt-tender-date-lot", "links"],
    page: 2, limit: 50, scope: "ACTIVE", paginationMode: "PAGE_NUMBER",
  });
});

test("ted_eu: a query syntax error is an isError result (wire)", async () => {
  const client = await connect(() => ({ status: 400, body: { message: "Syntax error in expert query at line 1, col 8", error: { type: "QUERY_SYNTAX_ERROR" } } }));
  const res = await client.callTool({ name: "search_postings", arguments: { query: "software" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "invalid_input");
});
