import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/sales/gleif_lei.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const RECORD = { type: "lei-records", id: "HWUPKR0MPOU8FGXBT394", attributes: { lei: "HWUPKR0MPOU8FGXBT394", entity: { legalName: { name: "Apple Inc." }, legalAddress: { addressLines: ["C/O Corporation Service Company"], city: "Glendale", region: "US-CA", country: "US", postalCode: "91203" }, status: "ACTIVE", creationDate: "1977-01-03T00:00:00Z", legalForm: { id: "H1UM" } } }, links: { self: "https://api.gleif.org/api/v1/lei-records/HWUPKR0MPOU8FGXBT394" } };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, {}, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("gleif: tools follow the sales vocabulary with no credentials (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_company", "me", "search"]);
  assert.equal(tools.find((t) => t.name === "get_company")._meta["platform_mcp/endpoint"], "/lei-records/{id}");
});

test("gleif: search maps the JSON:API record and sends the documented filters (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { meta: { pagination: { currentPage: 1, perPage: 25, total: 1, lastPage: 1 } }, data: [RECORD] } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "Apple Inc.", country: "US" } });
  assert.equal(res.isError, false);
  const c = res.structuredContent.companies[0];
  assert.equal(c.id, "HWUPKR0MPOU8FGXBT394"); assert.equal(c.name, "Apple Inc."); assert.equal(c.country, "US"); assert.equal(c.address, "C/O Corporation Service Company");
  assert.equal(res.structuredContent.total, 1);
  assert.equal(seen.url.searchParams.get("filter[entity.legalName]"), "Apple Inc."); assert.equal(seen.url.searchParams.get("filter[entity.legalAddress.country]"), "US");
  assert.equal(seen.url.searchParams.get("page[size]"), "25"); assert.equal(seen.url.searchParams.get("page[number]"), "1");
  assert.equal(seen.init.headers.Authorization, undefined);
});

test("gleif: unknown LEI is an invalid_input result (wire)", async () => {
  const res = await (await connect(() => ({ status: 404, body: { errors: [{ status: "404" }] } }))).callTool({ name: "get_company", arguments: { id: "NOPE" } });
  assert.equal(res.isError, true); assert.equal(res.structuredContent.error, "not_found"); assert.equal(res.structuredContent.http_status, 404);
});
