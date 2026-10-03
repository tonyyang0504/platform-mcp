import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/tenderned.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("tenderned: keyless TNS list with 0-based page (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { content: [{ publicatieId: "441637", aanbestedingNaam: "Riolering", opdrachtgeverNaam: "Gemeente Haarlemmermeer", publicatieDatum: "2026-09-25", link: { href: "https://www.tenderned.nl/aankondigingen/overzicht/441637" } }], totalElements: 5 } }; });
  const res = await client.callTool({ name: "search_postings", arguments: { page: 3, limit: 10 } });
  assert.equal(res.isError, false);
  assert.equal(seen.pathname, "/papi/tenderned-rs-tns/v2/publicaties");
  assert.equal(seen.searchParams.get("page"), "2");
  assert.equal(seen.searchParams.get("size"), "10");
  assert.equal(res.structuredContent.postings[0].buyer, "Gemeente Haarlemmermeer");
});
