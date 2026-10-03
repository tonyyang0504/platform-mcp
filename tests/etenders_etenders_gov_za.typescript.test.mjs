import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/etenders_etenders_gov_za.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const REL = { ocid: "ocds-9t57fa-171582", tender: { title: "NB124/2026 ", description: "SHE & FIRST AID TRAINING", value: { amount: 0, currency: "ZAR" }, tenderPeriod: { startDate: "2026-09-24T00:00:00Z", endDate: "2026-09-30T09:00:00Z" } }, buyer: { name: "Tourism" } };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, {}, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("etenders_za: search sends the date window and paging (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { releases: [REL] } }; });
  const res = await client.callTool({ name: "search_postings", arguments: { query: "ignored", page: 2, limit: 5 } });
  assert.equal(res.isError, false);
  assert.equal(seen.pathname, "/api/OCDSReleases");
  assert.equal(seen.searchParams.get("PageNumber"), "2");
  assert.equal(seen.searchParams.get("PageSize"), "5");
  assert.match(seen.searchParams.get("dateFrom"), /^\d{4}-\d{1,2}-01T00:00:00Z$/);
  assert.equal(seen.searchParams.get("query"), null);
  assert.equal(res.structuredContent.postings[0].buyer, "Tourism");
});

test("etenders_za: get_posting hits release/{ocid} (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: REL }; });
  const res = await client.callTool({ name: "get_posting", arguments: { id: "ocds-9t57fa-171582" } });
  assert.equal(seen.pathname, "/api/OCDSReleases/release/ocds-9t57fa-171582");
  assert.equal(res.structuredContent.deadline, "2026-09-30T09:00:00Z");
});
