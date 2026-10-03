import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/naver_search_ads.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_NAVER_SEARCH_ADS_API_KEY: "nv-license", PLATFORM_MCP_NAVER_SEARCH_ADS_SECRET_KEY: "nv-secret-key-xyz", PLATFORM_MCP_NAVER_SEARCH_ADS_CUSTOMER_ID: "1234567" });

test("naver_search_ads update_budget: X-Signature over timestamp.method.path, budget body (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { nccCampaignId: "cmp-1", dailyBudget: 70000 } }; });
  const res = await client.callTool({ name: "update_budget", arguments: { campaign_id: "cmp-1", daily_budget: 70000 } });
  assert.equal(res.isError, false);
  const h = seen[0].init.headers;
  assert.equal(seen[0].init.method, "PUT");
  assert.equal(seen[0].url.href, "https://api.searchad.naver.com/ncc/campaigns/cmp-1?fields=budget");
  assert.equal(h["X-API-KEY"], "nv-license");
  assert.equal(h["X-Customer"], "1234567");
  const expected = createHmac("sha256", "nv-secret-key-xyz").update(`${h["X-Timestamp"]}.PUT./ncc/campaigns/cmp-1`).digest("base64");
  assert.equal(h["X-Signature"], expected);
  assert.deepEqual(JSON.parse(seen[0].init.body), { nccCampaignId: "cmp-1", customerId: 1234567, useDailyBudget: true, dailyBudget: 70000 });
});

test("naver_search_ads pause_resume: fields=userLock, JSON boolean (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { nccCampaignId: "cmp-1", userLock: false } }; });
  const res = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "cmp-1", action: "resume" } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].init.method, "PUT");
  assert.equal(seen[0].url.searchParams.get("fields"), "userLock");
  assert.deepEqual(JSON.parse(seen[0].init.body), { nccCampaignId: "cmp-1", customerId: 1234567, userLock: false });
});
