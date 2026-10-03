import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/arbeidsplassen.json", import.meta.url), "utf8"));
const UUID = "9f47616c-718f-484a-8c77-4db72302d8b9";
const LINE = { id: UUID, url: `/api/v1/feedentry/${UUID}`, title: "Veterinærpatolog", content_text: "Stillingsannonse", date_modified: "2026-09-24T14:55:33.107613+02:00", _feed_entry: { uuid: UUID, status: "ACTIVE", title: "Veterinærpatolog", businessName: "Veterinærinstituttet", municipal: "ÅS" } };
const ENTRY = { uuid: UUID, status: "ACTIVE", ad_content: { uuid: UUID, published: "2026-09-24T00:00:00+02:00", title: "Veterinærpatolog", description: "<h2>Om stillingen</h2>", workLocations: [{ country: "NORGE", city: "ÅS", municipal: "ÅS" }], applicationUrl: "https://jobseeker.jobbnorge.no/apply/300870", link: `https://arbeidsplassen.nav.no/stillinger/stilling/${UUID}`, employer: { name: "Veterinærinstituttet", orgnr: null } } };
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { token: "JWT.PUBLIC.TOKEN" }, 50, "test", fakeFetch(handler)));
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
  assert.deepEqual(search.inputSchema.required, ["query"]);
  assert.equal(search._meta["platform_mcp/endpoint"], "/api/v1/feed");
  assert.equal(search._meta["platform_mcp/docs"], "https://pam-stilling-feed.nav.no/swagger");
});

test("search reads the newest feed page with the bearer token and sends no query (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { version: "1.0", id: "906c38d3", next_url: null, next_id: null, items: [LINE] } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "veterinær", location: "Ås", page: 2, limit: 5 } });
  assert.equal(res.isError, false);
  const p = res.structuredContent.postings[0];
  assert.equal(p.id, UUID);
  assert.equal(p.title, "Veterinærpatolog");
  assert.equal(p.company, "Veterinærinstituttet");
  assert.equal(p.location, "ÅS");
  assert.equal(p.raw._feed_entry.status, "ACTIVE");
  assert.equal(res.structuredContent.total, null);
  assert.equal(seen.init.headers.Authorization, "Bearer JWT.PUBLIC.TOKEN");
  assert.equal(seen.url.pathname, "/api/v1/feed");
  assert.deepEqual([...seen.url.searchParams.entries()], [["last", "true"]]);
});

test("get_posting maps the ad_content of a feed entry (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: ENTRY }; });
  const res = await client.callTool({ name: "get_posting", arguments: { id: UUID } });
  assert.equal(res.isError, false);
  assert.equal(seen.pathname, `/api/v1/feedentry/${UUID}`);
  assert.equal(res.structuredContent.id, UUID);
  assert.equal(res.structuredContent.company, "Veterinærinstituttet");
  assert.equal(res.structuredContent.url, `https://arbeidsplassen.nav.no/stillinger/stilling/${UUID}`);
  assert.equal(res.structuredContent.posted_at, "2026-09-24T00:00:00+02:00");
  assert.equal(res.structuredContent.raw.applicationUrl, "https://jobseeker.jobbnorge.no/apply/300870");
});

test("expired token is an isError auth_error result that does not echo the token (wire)", async () => {
  const client = await connect(() => ({ status: 401, body: { error: "Unauthorized" } }));
  const res = await client.callTool({ name: "search", arguments: { query: "x" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.equal(res.structuredContent.http_status, 401);
  assert.ok(!JSON.stringify(res.structuredContent).includes("JWT.PUBLIC.TOKEN"));
});
