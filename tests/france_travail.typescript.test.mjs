import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/france_travail.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const dig = (o, p) => p.split(".").reduce((a, k) => (a == null ? a : a[k]), o);
process.env.PLATFORM_MCP_FRANCE_TRAVAIL_CLIENT_ID = "ft-cid";
process.env.PLATFORM_MCP_FRANCE_TRAVAIL_CLIENT_SECRET = "ft-SECRETvalue";

async function connect(handler) {
  const tokens = [];
  globalThis.fetch = fakeFetch((url, init) => {
    if (url.href.split("?")[0] === "https://entreprise.francetravail.fr/connexion/oauth2/access_token") { tokens.push(init); return { body: {"access_token": "FT-TOKEN-abc", "token_type": "Bearer", "expires_in": 1499, "scope": "api_offresdemploiv2 o2dsoffre"} }; }
    return handler(url, init);
  });
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  client.tokens = tokens;
  return client;
}

test("france_travail: tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_posting", "search"]);
  for (const t of tools) { assert.equal(t.inputSchema.additionalProperties, false); assert.ok(t.title); }
});

test("france_travail: search maps documented fields (main, wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 206, body: {"resultats": [{"id": "048KLTP", "intitule": "Développeur", "entreprise": {"nom": "ACME"}, "lieuTravail": {"libelle": "75 - Paris"}, "origineOffre": {"urlOrigine": "https://candidat.francetravail.fr/offres/recherche/detail/048KLTP"}, "dateCreation": "2026-09-20T10:00:00Z", "description": "Poste"}], "filtresPossibles": []} }; });
  const res = await client.callTool({ name: "search", arguments: {"query": "informatique"} });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.deepEqual(dig(res.structuredContent, "postings.0.id"), "048KLTP");
  assert.deepEqual(dig(res.structuredContent, "postings.0.company"), "ACME");
  assert.deepEqual(dig(res.structuredContent, "postings.0.location"), "75 - Paris");
  assert.deepEqual(dig(res.structuredContent, "total"), null);
  assert.equal(seen.url.href.split("?")[0], "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search");
  assert.equal(seen.init.method, "GET");
  assert.equal(seen.url.searchParams.get("motsCles"), "informatique");
  assert.equal(seen.url.searchParams.has("range"), false);
  assert.equal((seen.init.headers["Authorization"] ?? seen.init.headers["authorization"]), "Bearer FT-TOKEN-abc");
  assert.deepEqual(Object.fromEntries(new URLSearchParams(client.tokens.at(-1).body)), {"grant_type": "client_credentials", "client_id": "ft-cid", "client_secret": "ft-SECRETvalue", "scope": "api_offresdemploiv2 o2dsoffre"});
});

test("france_travail: get_posting maps documented fields (extra, wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 200, body: {"id": "048KLTP", "intitule": "Développeur", "description": "Texte", "dateCreation": "2026-09-20T10:00:00Z"} }; });
  const res = await client.callTool({ name: "get_posting", arguments: {"id": "048KLTP"} });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.deepEqual(dig(res.structuredContent, "id"), "048KLTP");
  assert.deepEqual(dig(res.structuredContent, "title"), "Développeur");
  assert.deepEqual(dig(res.structuredContent, "description"), "Texte");
  assert.equal(seen.url.href.split("?")[0], "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/048KLTP");
  assert.equal(seen.init.method, "GET");

});

test("france_travail: rate limit is an isError result (wire)", async () => {
  const client = await connect(() => ({ status: 429, headers: { "Retry-After": "30" } }));
  const res = await client.callTool({ name: "get_posting", arguments: {"id": "X"} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
  assert.equal(res.structuredContent.retry_after_seconds, 30);
});
