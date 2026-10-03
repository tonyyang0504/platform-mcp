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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/smartnews_ads.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_SMARTNEWS_ADS_CLIENT_ID: "12345", PLATFORM_MCP_SMARTNEWS_ADS_CLIENT_SECRET: "snsecret", PLATFORM_MCP_SMARTNEWS_ADS_AD_ACCOUNT_ID: "777" });

test("smartnews_ads get_report: insights with repeated fields (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.pathname === "/api/oauth/v1/access_tokens") return { body: { access_token: "SNJWTTOKEN", expires_in: 86400 } };
    return { body: { data: [{ id: 55, metadata: { name: "Launch" }, metrics: { viewable_impression: 900, budget_spent: "108" } }] } };
  });
  const res = await client.callTool({ name: "get_report", arguments: { account_id: "777", date_from: "2026-09-01", date_to: "2026-09-07" } });
  assert.equal(res.isError, false);
  assert.equal(seen[1].url.pathname, "/api/ma/v3/ad_accounts/777/insights/campaigns");
  assert.deepEqual(seen[1].url.searchParams.getAll("fields"), ["metadata_name", "metrics_viewable_impression", "metrics_click", "metrics_ctr", "metrics_cpc", "metrics_budget_spent"]);
  assert.equal(seen[1].url.searchParams.get("until"), "2026-09-07T23:59:59Z");
  assert.equal(res.structuredContent.rows[0].spend, "108");
});
