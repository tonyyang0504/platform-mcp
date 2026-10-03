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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/the_trade_desk.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_THE_TRADE_DESK_API_TOKEN: "ttd-tok-123", PLATFORM_MCP_THE_TRADE_DESK_PARTNER_ID: "p4rtn3r" });

test("the_trade_desk list_campaigns: POST query with offset paging and TTD-Auth (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    return { body: { Result: [{ CampaignId: "c9", CampaignName: "Fall", Availability: "Available", Budget: { Amount: 5000, CurrencyCode: "USD" } }], TotalFilteredCount: 31 } };
  });
  const res = await client.callTool({ name: "list_campaigns", arguments: { account_id: "adv1", page: 2, limit: 10 } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].url.pathname, "/v3/campaign/query/advertiser");
  assert.equal(seen[0].init.headers["TTD-Auth"], "ttd-tok-123");
  assert.deepEqual(JSON.parse(seen[0].init.body), { AdvertiserId: "adv1", PageStartIndex: 10, PageSize: 10 });
  assert.equal(res.structuredContent.campaigns[0].budget, 5000);
  assert.equal(res.structuredContent.total, 31);
});

test("the_trade_desk update_budget: PUT /v3/campaign with DailyBudget Money (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { CampaignId: "c9" } }; });
  const res = await client.callTool({ name: "update_budget", arguments: { campaign_id: "c9", daily_budget: 250.5, currency: "USD" } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].init.method, "PUT");
  assert.deepEqual(JSON.parse(seen[0].init.body), { CampaignId: "c9", DailyBudget: { Amount: 250.5, CurrencyCode: "USD" } });
  assert.equal(res.structuredContent.status, "updated");
});
