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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/apple_search_ads.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_APPLE_SEARCH_ADS_CLIENT_ID: "SEARCHADS.abc", PLATFORM_MCP_APPLE_SEARCH_ADS_CLIENT_SECRET: "eyJ.jwt.sig", PLATFORM_MCP_APPLE_SEARCH_ADS_AP_CONTEXT: "adAccountId=123456789" });

test("apple_search_ads pause_resume: searchadsorg token, X-AP-Context, PUT status (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.hostname === "appleid.apple.com") return { body: { access_token: "APLTOKEN", expires_in: 3600 } };
    return { body: { result: { id: 111, status: "PAUSED" } } };
  });
  const res = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "111", action: "pause" } });
  assert.equal(res.isError, false);
  assert.equal(form(seen[0].init.body).scope, "searchadsorg");
  assert.equal(seen[1].init.method, "PUT");
  assert.equal(seen[1].url.href, "https://api.ads.apple.com/v1/campaigns/111");
  assert.equal(seen[1].init.headers["X-AP-Context"], "adAccountId=123456789");
  assert.deepEqual(JSON.parse(seen[1].init.body), { status: "PAUSED" });
  assert.equal(res.structuredContent.status, "PAUSED");
});
