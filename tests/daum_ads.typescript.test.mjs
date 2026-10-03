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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/daum_ads.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_DAUM_ADS_BUSINESS_TOKEN: "KBIZTOKEN", PLATFORM_MCP_DAUM_ADS_AD_ACCOUNT_ID: "1111111111" });

test("daum_ads update_budget: PATCH dailyBudget with adAccountId header (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { raw: "" }; });
  const res = await client.callTool({ name: "update_budget", arguments: { campaign_id: "333", daily_budget: 20000 } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].init.method, "PATCH");
  assert.equal(seen[0].url.href, "https://api.keywordad.kakao.com/openapi/v1/campaigns/333/dailyBudget");
  assert.equal(seen[0].init.headers.Authorization, "Bearer KBIZTOKEN");
  assert.equal(seen[0].init.headers.adAccountId, "1111111111");
  assert.deepEqual(JSON.parse(seen[0].init.body), { dailyBudgetAmount: 20000 });
  assert.equal(res.structuredContent.status, "updated");
});
