import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/trademe_nz.json", import.meta.url), "utf8"));
const json = (status, body) => ({ status, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null) }, text: async () => JSON.stringify(body) });
const CREDS = { consumer_key: "4E0D082355116884742E5F33B8A199F411", consumer_secret: "160FCF77971DC92A38596288DB071A8CA5" };
const AUTH = "OAuth oauth_consumer_key=4E0D082355116884742E5F33B8A199F411, oauth_signature_method=PLAINTEXT, oauth_signature=160FCF77971DC92A38596288DB071A8CA5%26";

async function connect(handler) {
  const log = [];
  const fetcher = async (url, init) => { log.push({ url: new URL(url), init }); return handler(new URL(url)); };
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, CREDS, 50, "test", fetcher));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  client.log = log;
  return client;
}

test("trademe_nz: jobs search with the PLAINTEXT OAuth header (main, wire)", async () => {
  const client = await connect(() => json(200, { TotalCount: 3, List: [{ ListingId: 5012345678, Title: "Senior Designer", Company: "Acme Ltd", ShortDescription: "Design things" }] }));
  const res = await client.callTool({ name: "search_postings", arguments: { query: "designer", limit: 100 } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.equal(res.structuredContent.postings[0].id, "5012345678"); assert.equal(res.structuredContent.postings[0].buyer, "Acme Ltd");
  const seen = client.log[0];
  assert.equal(seen.url.href.split("?")[0], "https://api.trademe.co.nz/v1/Search/Jobs.json");
  assert.equal(seen.init.headers.Authorization, AUTH);
  assert.equal(seen.url.searchParams.get("search_string"), "designer"); assert.equal(seen.url.searchParams.get("rows"), "25");
});

test("trademe_nz: get_posting reads the listing (wire)", async () => {
  const client = await connect(() => json(200, { ListingId: 5012345678, Title: "Senior Designer", Company: "Acme Ltd", Body: "Full" }));
  const res = await client.callTool({ name: "get_posting", arguments: { id: "5012345678" } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.equal(res.structuredContent.description, "Full");
  assert.equal(client.log[0].url.pathname, "/v1/Listings/5012345678.json");
});

test("trademe_nz: 401 is an auth_error (wire)", async () => {
  const client = await connect(() => json(401, { ErrorDescription: "Invalid signature" }));
  const res = await client.callTool({ name: "search_postings", arguments: {} });
  assert.equal(res.isError, true); assert.equal(res.structuredContent.error, "auth_error");
});
