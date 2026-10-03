import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/sales/uk_companies_house.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_key: "k" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("companies house: tools follow the sales vocabulary (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_company", "me", "search"]);
  const search = tools.find((t) => t.name === "search");
  assert.equal(search.annotations.readOnlyHint, true);
  assert.equal(search.title, "Search companies");
  assert.equal(search._meta["platform_mcp/endpoint"], "/search/companies");
});

test("companies house: search maps documented fields with Basic key auth (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { items: [{ company_number: "00102498", title: "BP P.L.C.", date_of_creation: "1909-04-14", address_snippet: "1 St James's Square, London, SW1Y 4PD", address: { country: "United Kingdom" }, links: { self: "/company/00102498" } }], total_results: 1 } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "bp" } });
  assert.equal(res.isError, false);
  const c = res.structuredContent.companies[0];
  assert.equal(c.id, "00102498"); assert.equal(c.name, "BP P.L.C."); assert.equal(c.country, "United Kingdom"); assert.equal(c.founded, "1909-04-14");
  assert.equal(res.structuredContent.total, 1);
  assert.equal(seen.url.searchParams.get("q"), "bp"); assert.equal(seen.url.searchParams.get("items_per_page"), "25"); assert.equal(seen.url.searchParams.get("start_index"), "0");
  assert.equal(seen.init.headers.Authorization, "Basic " + Buffer.from("k:").toString("base64"));
});

test("companies house: 429 is an isError result (wire)", async () => {
  const res = await (await connect(() => ({ status: 429, headers: { "Retry-After": "300" } }))).callTool({ name: "get_company", arguments: { id: "X" } });
  assert.equal(res.isError, true); assert.equal(res.structuredContent.error, "rate_limited"); assert.equal(res.structuredContent.retry_after_seconds, 300);
});
