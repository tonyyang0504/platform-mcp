import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/arbeitsagentur.json", import.meta.url), "utf8"));
const HIT = { stellenangebotsTitel: "Softwareentwickler Python/C# (m/w/d)", gehaltsspanneVon: 50000, gehaltsspanneBis: 60000, stellenlokationen: [{ adresse: { plz: "88046", ort: "Friedrichshafen" } }], datumErsteVeroeffentlichung: "2026-09-07", firma: "FERCHAU GmbH", referenznummer: "12265-271357_JB5240730-S" };
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_key: "jobboerse-jobsuche" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("tools follow the vocabulary and carry annotations (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_posting", "search"]);
  const search = tools.find((t) => t.name === "search");
  assert.equal(search.annotations.readOnlyHint, true);
  assert.equal(search.annotations.destructiveHint, false);
  assert.deepEqual(search.inputSchema.required, ["query"]);
  assert.equal(search._meta["platform_mcp/endpoint"], "/pc/v6/jobs");
  assert.equal(search._meta["platform_mcp/docs"], "https://jobsuche.api.bund.dev/");
});

test("search sends the public client id header and maps v6 fields (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { ergebnisliste: [HIT], maxErgebnisse: 2865, page: 2, size: 50 } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "python", location: "Berlin", page: 2, limit: 50 } });
  assert.equal(res.isError, false);
  const p = res.structuredContent.postings[0];
  assert.equal(p.id, "12265-271357_JB5240730-S");
  assert.equal(p.company, "FERCHAU GmbH");
  assert.equal(p.location, "Friedrichshafen");
  assert.equal(p.salary_min, 50000);
  assert.equal(res.structuredContent.total, 2865);
  assert.equal(res.structuredContent.next_page, null);
  assert.equal(seen.init.headers["X-API-Key"], "jobboerse-jobsuche");
  assert.equal(seen.url.searchParams.get("was"), "python");
  assert.equal(seen.url.searchParams.get("wo"), "Berlin");
  assert.equal(seen.url.searchParams.get("page"), "2");
  assert.equal(seen.url.searchParams.get("size"), "50");
});

test("get_posting takes the base64 refnr and maps the description (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { ...HIT, stellenangebotsBeschreibung: "Die besten Köpfe ..." } }; });
  const res = await client.callTool({ name: "get_posting", arguments: { id: "MTIyNjUtMjcxMzU3X0pCNTI0MDczMC1T" } });
  assert.equal(res.isError, false);
  assert.equal(seen.pathname, "/jobboerse/jobsuche-service/pc/v4/jobdetails/MTIyNjUtMjcxMzU3X0pCNTI0MDczMC1T");
  assert.equal(res.structuredContent.id, "12265-271357_JB5240730-S");
  assert.equal(res.structuredContent.description, "Die besten Köpfe ...");
});

test("refused client id is an isError auth_error result (wire)", async () => {
  const client = await connect(() => ({ status: 403, body: "Forbidden" }));
  const res = await client.callTool({ name: "search", arguments: { query: "python" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.equal(res.structuredContent.http_status, 403);
});
