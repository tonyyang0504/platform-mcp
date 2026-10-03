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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/yahoo_japan_ads.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_YAHOO_JAPAN_ADS_CLIENT_ID: "yjcid", PLATFORM_MCP_YAHOO_JAPAN_ADS_CLIENT_SECRET: "yjsecret", PLATFORM_MCP_YAHOO_JAPAN_ADS_REFRESH_TOKEN: "yjrefresh1", PLATFORM_MCP_YAHOO_JAPAN_ADS_BASE_ACCOUNT_ID: "1000", PLATFORM_MCP_YAHOO_JAPAN_ADS_ACCOUNT_ID: "2000" });

test("yahoo_japan_ads update_budget: CampaignService/set operand with base account header (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.hostname === "biz-oauth.yahoo.co.jp") return { body: { access_token: "YJTOKEN1", expires_in: 3600 } };
    return { body: { rval: { values: [{ operationSucceeded: true, campaign: { campaignId: 11 } }] } } };
  });
  const res = await client.callTool({ name: "update_budget", arguments: { campaign_id: "11", daily_budget: 8000 } });
  assert.equal(res.isError, false);
  assert.equal(seen[1].url.href, "https://ads-search.yahooapis.jp/api/v20/CampaignService/set");
  assert.equal(seen[1].init.headers["x-z-base-account-id"], "1000");
  assert.deepEqual(JSON.parse(seen[1].init.body), { accountId: 2000, operand: [{ campaignId: 11, budget: { amount: 8000 } }] });
  assert.equal(res.structuredContent.operation_succeeded, true);
});
