import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/boamp.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const REC = { idweb: "26-91551", objet: "Mission de maîtrise d'œuvre", nomacheteur: "COMMUNE DE VICHY", dateparution: "2026-09-24", datelimitereponse: "2026-10-26T11:00:00+00:00", url_avis: "https://www.boamp.fr/pages/avis/?q=idweb:26-91551", descripteur_libelle: ["Maîtrise d'oeuvre"] };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, {}, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("boamp: search sends a quoted ODSQL where, refine and offset (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { total_count: 209, results: [REC] } }; });
  const res = await client.callTool({ name: "search_postings", arguments: { query: "toiture vichy", category: "Bâtiment", page: 2, limit: 10 } });
  assert.equal(res.isError, false);
  assert.equal(seen.pathname, "/api/explore/v2.1/catalog/datasets/boamp/records");
  assert.equal(seen.searchParams.get("where"), '"toiture vichy"');
  assert.equal(seen.searchParams.get("refine"), "descripteur_libelle:Bâtiment");
  assert.equal(seen.searchParams.get("offset"), "10");
  assert.equal(seen.searchParams.get("order_by"), "dateparution desc");
  assert.equal(res.structuredContent.postings[0].id, "26-91551");
  assert.equal(res.structuredContent.total, 209);
});

test("boamp: get_posting filters by idweb; no match is isError (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { total_count: 0, results: [] } }; });
  const res = await client.callTool({ name: "get_posting", arguments: { id: "26-91551" } });
  assert.equal(seen.searchParams.get("where"), 'idweb="26-91551"');
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "not_found");
});
