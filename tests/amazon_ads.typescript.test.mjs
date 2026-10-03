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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/amazon_ads.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_AMAZON_ADS_CLIENT_ID: "amzn1.application-oa2-client.abc", PLATFORM_MCP_AMAZON_ADS_CLIENT_SECRET: "amzsecret", PLATFORM_MCP_AMAZON_ADS_REFRESH_TOKEN: "Atzr|rt", PLATFORM_MCP_AMAZON_ADS_API_HOST: "advertising-api.amazon.com", PLATFORM_MCP_AMAZON_ADS_PROFILE_ID: "3312345678901234" });

test("amazon_ads list_accounts: LWA refresh in the body, ClientId + Scope headers (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.href === "https://api.amazon.com/auth/o2/token") return { body: { access_token: "Atza|AT", expires_in: 3600 } };
    return { body: [{ profileId: 3312345678901234, countryCode: "US", currencyCode: "USD", accountInfo: { id: "A2XYZ", type: "seller", name: "Shop LLC" } }] };
  });
  const res = await client.callTool({ name: "list_accounts", arguments: {} });
  assert.equal(res.isError, false);
  assert.deepEqual(form(seen[0].init.body), { grant_type: "refresh_token", refresh_token: "Atzr|rt", client_id: "amzn1.application-oa2-client.abc", client_secret: "amzsecret" });
  assert.equal(seen[1].url.href, "https://advertising-api.amazon.com/v2/profiles");
  assert.equal(seen[1].init.headers["Amazon-Advertising-API-ClientId"], "amzn1.application-oa2-client.abc");
  assert.equal(seen[1].init.headers["Amazon-Advertising-API-Scope"], "3312345678901234");
  const a = res.structuredContent.accounts[0];
  assert.equal(a.id, "3312345678901234"); assert.equal(a.name, "Shop LLC"); assert.equal(a.currency, "USD");
});

test("amazon_ads refused refresh token is an auth_error without secrets (wire)", async () => {
  const client = await connect(SPEC, () => ({ status: 400, body: { error: "invalid_grant", error_description: "The request has an invalid grant parameter : refresh_token" } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.ok(!JSON.stringify(res.structuredContent).includes("amzsecret"));
});

test("amazon_ads SP v3 list and pause keep the vendor media type (wire)", async () => {
  const VND = "application/vnd.spCampaign.v3+json";
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.href === "https://api.amazon.com/auth/o2/token") return { body: { access_token: "Atza|AT", expires_in: 3600 } };
    if (url.pathname === "/sp/campaigns/list") return { headers: { "content-type": VND }, body: { campaigns: [{ campaignId: "3001", name: "SP auto", state: "PAUSED", budget: { budget: 20, budgetType: "DAILY" } }], totalResults: 1 } };
    return { status: 207, headers: { "content-type": VND }, body: { campaigns: { success: [{ campaignId: "3001", index: 0, campaign: { campaignId: "3001", state: "PAUSED" } }], error: [] } } };
  });
  const list = await client.callTool({ name: "list_campaigns", arguments: { account_id: "3312345678901234", status: "PAUSED" } });
  assert.equal(list.isError, false);
  const lreq = seen.find((s) => s.url.pathname === "/sp/campaigns/list");
  assert.equal(lreq.init.headers["Content-Type"], VND); assert.equal(lreq.init.headers.Accept, VND);
  assert.deepEqual(JSON.parse(lreq.init.body), { maxResults: 25, stateFilter: { include: ["PAUSED"] } });
  assert.equal(list.structuredContent.campaigns[0].budget, 20);
  const res = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "3001", action: "pause" } });
  assert.equal(res.isError, false);
  const put = seen.find((s) => s.init.method === "PUT");
  assert.equal(put.init.headers["Content-Type"], VND);
  assert.deepEqual(JSON.parse(put.init.body), { campaigns: [{ campaignId: "3001", state: "PAUSED" }] });
  assert.equal(res.structuredContent.status, "PAUSED");
});
