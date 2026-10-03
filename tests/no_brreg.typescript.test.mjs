import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/sales/no_brreg.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const ENHET = { organisasjonsnummer: "923609016", navn: "EQUINOR ASA", hjemmeside: "www.equinor.com", forretningsadresse: { landkode: "NO", adresse: ["Forusbeen 50"] }, naeringskode1: { kode: "06.100", beskrivelse: "Utvinning av råolje" }, antallAnsatte: 21272, stiftelsesdato: "1972-09-18" };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, {}, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("brreg: tools follow the sales vocabulary (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_company", "me", "search"]);
  assert.equal(tools.find((t) => t.name === "search")._meta["platform_mcp/endpoint"], "/enheter");
});

test("brreg: search sends a zero-based page (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { _embedded: { enheter: [ENHET] }, page: { size: 1, totalElements: 240, totalPages: 240, number: 1 } } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "equinor", page: 2, limit: 1 } });
  assert.equal(res.isError, false);
  const c = res.structuredContent.companies[0];
  assert.equal(c.id, "923609016"); assert.equal(c.name, "EQUINOR ASA"); assert.equal(c.country, "NO"); assert.equal(c.address, "Forusbeen 50");
  assert.equal(res.structuredContent.total, 240); assert.equal(res.structuredContent.next_page, 3);
  assert.equal(seen.searchParams.get("navn"), "equinor"); assert.equal(seen.searchParams.get("size"), "1"); assert.equal(seen.searchParams.get("page"), "1");
});

test("brreg: 404 is an isError result (wire)", async () => {
  const client = await connect(() => ({ status: 404 }));
  const res = await client.callTool({ name: "get_company", arguments: { id: "000000000" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "not_found");
});
