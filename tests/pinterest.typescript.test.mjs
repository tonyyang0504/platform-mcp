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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/pinterest.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_PINTEREST_CLIENT_ID: "1480000", PLATFORM_MCP_PINTEREST_CLIENT_SECRET: "pinsecret", PLATFORM_MCP_PINTEREST_REFRESH_TOKEN: "pinr.abc", PLATFORM_MCP_PINTEREST_AD_ACCOUNT_ID: "549755885175" });

test("pinterest refresh grant with Basic auth, then campaign analytics rows (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.pathname === "/v5/oauth/token") return { body: { access_token: "pina_AT", expires_in: 2592000 } };
    return { body: [{ CAMPAIGN_ID: "626735565838", DATE: "2026-09-01", SPEND_IN_DOLLAR: 12.5, IMPRESSION_1: 1000, CLICKTHROUGH_1: 17 }] };
  });
  const res = await client.callTool({ name: "get_report", arguments: { account_id: "549755885175", campaign_id: "626735565838", date_from: "2026-09-01", date_to: "2026-09-07" } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].init.headers.Authorization, "Basic " + Buffer.from("1480000:pinsecret").toString("base64"));
  assert.deepEqual(form(seen[0].init.body), { grant_type: "refresh_token", refresh_token: "pinr.abc" });
  assert.equal(seen[1].url.pathname, "/v5/ad_accounts/549755885175/campaigns/analytics");
  assert.equal(seen[1].url.searchParams.get("campaign_ids"), "626735565838");
  assert.equal(seen[1].init.headers.Authorization, "Bearer pina_AT");
  const r = res.structuredContent.rows[0];
  assert.equal(r.date, "2026-09-01"); assert.equal(r.spend, 12.5); assert.equal(r.clicks, 17);
});

test("pinterest rate limit is a rate_limited result (wire)", async () => {
  const client = await connect(SPEC, (url) => url.pathname === "/v5/oauth/token" ? { body: { access_token: "pina_AT", expires_in: 3600 } } : { status: 429, headers: { "Retry-After": "12" }, body: { code: 8, message: "Rate limit exceeded" } });
  const res = await client.callTool({ name: "list_accounts", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
});

test("pinterest update_budget and pause_resume PATCH a top-level array (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.pathname === "/v5/oauth/token") return { body: { access_token: "pina_AT", expires_in: 3600 } };
    return { body: { items: [{ data: { id: "626735565838", status: "PAUSED" }, exceptions: [] }] } };
  });
  const r1 = await client.callTool({ name: "update_budget", arguments: { campaign_id: "626735565838", daily_budget: 25000000 } });
  assert.equal(r1.isError, false);
  const patch = seen.filter((s) => s.init.method === "PATCH");
  assert.equal(patch[0].url.pathname, "/v5/ad_accounts/549755885175/campaigns");
  assert.deepEqual(JSON.parse(patch[0].init.body), [{ id: "626735565838", daily_spend_cap: 25000000 }]);
  const r2 = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "626735565838", action: "pause" } });
  assert.equal(r2.structuredContent.status, "PAUSED");
  assert.deepEqual(JSON.parse(seen.filter((s) => s.init.method === "PATCH")[1].init.body), [{ id: "626735565838", status: "PAUSED" }]);
});
