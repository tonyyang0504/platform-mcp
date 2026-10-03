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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/amazon_fire_tv_ads.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_AMAZON_FIRE_TV_ADS_CLIENT_ID: "amzn1.cid", PLATFORM_MCP_AMAZON_FIRE_TV_ADS_CLIENT_SECRET: "lwasecret", PLATFORM_MCP_AMAZON_FIRE_TV_ADS_REFRESH_TOKEN: "Atzr|refresh", PLATFORM_MCP_AMAZON_FIRE_TV_ADS_API_HOST: "advertising-api.amazon.com", PLATFORM_MCP_AMAZON_FIRE_TV_ADS_PROFILE_ID: "3001" });

test("amazon_fire_tv_ads update_budget: PUT /st/campaigns with ST media type (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.hostname === "api.amazon.com") return { body: { access_token: "Atza|X", expires_in: 3600 } };
    return { status: 207, body: { campaigns: { success: [{ campaignId: "31", index: 0 }], error: [] } } };
  });
  const res = await client.callTool({ name: "update_budget", arguments: { campaign_id: "31", daily_budget: 99, currency: "USD" } });
  assert.equal(res.isError, false);
  assert.equal(seen[1].init.method, "PUT");
  assert.equal(seen[1].url.href, "https://advertising-api.amazon.com/st/campaigns");
  assert.equal(seen[1].init.headers["Content-Type"], "application/vnd.stCampaign.v1+json");
  assert.equal(seen[1].init.headers["Amazon-Advertising-API-Scope"], "3001");
  assert.deepEqual(JSON.parse(seen[1].init.body), { campaigns: [{ campaignId: "31", budgetSettings: { budget: { budgetValue: { amount: 99, budgetCurrencyCode: "USD" }, recurrenceType: "DAILY" } } }] });
  assert.equal(res.structuredContent.status, "updated");
});
