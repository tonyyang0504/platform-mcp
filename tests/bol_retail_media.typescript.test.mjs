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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/bol_retail_media.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_BOL_RETAIL_MEDIA_CLIENT_ID: "bol-cid", PLATFORM_MCP_BOL_RETAIL_MEDIA_CLIENT_SECRET: "bol-secret-123" });

test("bol_retail_media list_campaigns: basic token, POST list body (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.host === "login.bol.com") return { body: { access_token: "JWT1", expires_in: 299 } };
    return { body: { campaigns: [{ campaignId: "12345", name: "Herfst", state: "PAUSED", dailyBudget: { amount: 25, currency: "EUR" } }] } };
  });
  const res = await client.callTool({ name: "list_campaigns", arguments: { account_id: "x" } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].init.headers.Authorization, "Basic " + Buffer.from("bol-cid:bol-secret-123").toString("base64"));
  assert.equal(seen[1].url.href, "https://api.bol.com/advertiser/sponsored-products/campaign-management/campaigns/list");
  assert.equal(seen[1].init.headers.Authorization, "Bearer JWT1");
  assert.deepEqual(JSON.parse(seen[1].init.body), { page: 1, pageSize: 50 });
  assert.equal(res.structuredContent.campaigns[0].status, "PAUSED");
});
