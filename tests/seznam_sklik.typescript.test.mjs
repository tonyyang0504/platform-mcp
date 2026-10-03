import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (r.raw ?? JSON.stringify(r.body ?? {})) }; };
async function connect(spec, handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(spec);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/seznam_sklik.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_SEZNAM_SKLIK_REFRESH_TOKEN: "sklik-refresh-secret" });

test("seznam_sklik pause_resume: form refresh login, PATCH status suspend (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.pathname === "/v1/user/token") return { body: { access_token: "SKAT", expires_in: 3600 } };
    return { status: 204, raw: "" };
  });
  const res = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "123", action: "pause" } });
  assert.equal(res.isError, false);
  assert.deepEqual(Object.fromEntries(new URLSearchParams(String(seen[0].init.body))), { grant_type: "refresh_token", refresh_token: "sklik-refresh-secret" });
  assert.equal(seen[1].init.method, "PATCH");
  assert.equal(seen[1].url.href, "https://api.sklik.cz/v1/sklik/campaigns/123/");
  assert.equal(seen[1].init.headers.Authorization, "Bearer SKAT");
  assert.deepEqual(JSON.parse(seen[1].init.body), { status: "suspend" });
});

test("seznam_sklik list_campaigns: repeated a= attributes (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.pathname === "/v1/user/token") return { body: { access_token: "SKAT", expires_in: 3600 } };
    return { body: { items: [] } };
  });
  await client.callTool({ name: "list_campaigns", arguments: { account_id: "x" } });
  assert.deepEqual(seen[1].url.searchParams.getAll("a"), ["id", "name", "status", "type", "startDate", "endDate", "budget.id", "budget.dayBudget"]);
});
