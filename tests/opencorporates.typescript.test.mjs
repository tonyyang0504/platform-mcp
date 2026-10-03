import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/sales/opencorporates.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const COMPANY = { name: "BP P.L.C.", company_number: "00102498", jurisdiction_code: "gb", incorporation_date: "1909-04-14", registered_address_in_full: "1 St James's Square, London, SW1Y 4PD", current_status: "Active", opencorporates_url: "https://opencorporates.com/companies/gb/00102498" };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_token: "tok" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("opencorporates: tools follow the sales vocabulary (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_company", "me", "search"]);
  assert.equal(tools.find((t) => t.name === "me")._meta["platform_mcp/endpoint"], "/account_status");
});

test("opencorporates: search maps results.companies[].company and sends api_token (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { api_version: "0.4", results: { companies: [{ company: COMPANY }], page: 1, per_page: 25, total_pages: 1, total_count: 1 } } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "bp", country: "gb" } });
  assert.equal(res.isError, false);
  const c = res.structuredContent.companies[0];
  assert.equal(c.id, "00102498"); assert.equal(c.name, "BP P.L.C."); assert.equal(c.country, "gb"); assert.equal(c.url, "https://opencorporates.com/companies/gb/00102498");
  assert.equal(res.structuredContent.total, 1); assert.equal(res.structuredContent.next_page, null);
  assert.equal(seen.url.searchParams.get("q"), "bp"); assert.equal(seen.url.searchParams.get("country_code"), "gb"); assert.equal(seen.url.searchParams.get("api_token"), "tok");
  assert.equal(seen.init.headers.Authorization, undefined);
});

test("opencorporates: get_company takes jurisdiction/number and 401 is an auth_error (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return url.pathname.endsWith("/account_status") ? { status: 401, body: { error: "Invalid or missing API token" } } : { body: { api_version: "0.4", results: { company: COMPANY } } }; });
  const ok = await client.callTool({ name: "get_company", arguments: { id: "gb/00102498" } });
  assert.equal(ok.isError, false); assert.equal(seen.pathname, "/v0.4/companies/gb/00102498"); assert.equal(ok.structuredContent.name, "BP P.L.C.");
  const bad = await client.callTool({ name: "me", arguments: {} });
  assert.equal(bad.isError, true); assert.equal(bad.structuredContent.error, "auth_error");
});
