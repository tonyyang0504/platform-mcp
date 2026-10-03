import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/doordash_ads.json", import.meta.url), "utf8"));
const CREDS = { api_key: "DD-ADS-KEY-secret", campaign_type: "sb" };

async function connect(handler, log) {
  const f = async (url, init) => { log.push({ url: new URL(url), init }); const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => "application/json" }, text: async () => JSON.stringify(r.body ?? {}) }; };
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", f, a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("doordash_ads: campaign type path segment, bearer key and cents budget", async () => {
  const log = [];
  const c = await connect((url, init) => (init.method === "PUT" ? { body: { campaignId: "c-9" } } : { body: { campaigns: [{ campaignId: "c-9", name: "SB", status: "PAUSED" }] } }), log);
  const list = await c.callTool({ name: "list_campaigns", arguments: { account_id: "x", limit: 5 } });
  assert.equal(list.isError, false);
  assert.equal(list.structuredContent.campaigns[0].id, "c-9");
  assert.equal(log[0].url.pathname, "/ads/api/v1/sb/campaigns");
  assert.equal(log[0].url.searchParams.get("startIndex"), "0");
  assert.equal(log[0].init.headers.Authorization, "Bearer DD-ADS-KEY-secret");
  const up = await c.callTool({ name: "update_budget", arguments: { campaign_id: "c-9", daily_budget: 12.34 } });
  assert.equal(up.isError, false);
  assert.deepEqual(JSON.parse(log[1].init.body), { campaignId: "c-9", budget: { daily: { unitAmount: 1234 } } });
  const res = await c.callTool({ name: "pause_resume", arguments: { campaign_id: "c-9", action: "resume" } });
  assert.equal(res.isError, false);
  assert.deepEqual(JSON.parse(log[2].init.body), { campaignId: "c-9", status: "ACTIVE" });
});
