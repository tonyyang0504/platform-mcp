import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (r.raw ?? JSON.stringify(r.body ?? {})) }; };
const form = (body) => Object.fromEntries(new URLSearchParams(body));
async function connect(spec, handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(spec);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/adform.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_ADFORM_CLIENT_ID: "adf-cid", PLATFORM_MCP_ADFORM_CLIENT_SECRET: "adfsecret" });

test("adform list_campaigns: scoped client credentials, advertiser filter, offset paging (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.hostname === "id.adform.com") return { body: { access_token: "ADF", expires_in: 3600 } };
    return { body: [{ id: 77777, name: "Campaign 77777", budget: 10, status: "Active", currency: "DKK" }] };
  });
  const res = await client.callTool({ name: "list_campaigns", arguments: { account_id: "33333", page: 3, limit: 5 } });
  assert.equal(res.isError, false);
  const tok = form(seen[0].init.body);
  assert.equal(tok.grant_type, "client_credentials");
  assert.equal(tok.scope, "https://api.adform.com/scope/buyer.advertisers.readonly https://api.adform.com/scope/buyer.campaigns.api.readonly");
  assert.equal(seen[1].url.pathname, "/v1/buyer/campaigns");
  assert.equal(seen[1].url.searchParams.get("advertisers"), "33333");
  assert.equal(seen[1].url.searchParams.get("offset"), "10");
  assert.equal(seen[1].init.headers.Authorization, "Bearer ADF");
  assert.equal(res.structuredContent.campaigns[0].id, "77777");
});
