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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/digital_turbine.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_DIGITAL_TURBINE_MANAGEMENT_API_TOKEN: "dt-mgmt-secret" });

test("digital_turbine update_budget: x-api-key, GraphQL mutation variables (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { data: { offerCampaignBulkUpdateBids: { errors: [] } } } }; });
  const res = await client.callTool({ name: "update_budget", arguments: { campaign_id: "12", daily_budget: 2.3 } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].url.href, "https://acp-edge-api.fyber.com/graphql");
  assert.equal(seen[0].init.headers["x-api-key"], "dt-mgmt-secret");
  assert.deepEqual(JSON.parse(seen[0].init.body).variables, { offerCmsId: "12", bidsList: [{ dailyBudget: "2.3" }] });
  assert.equal(res.structuredContent.status, "submitted");
});

test("digital_turbine pause_resume: GraphQL Boolean offerEnabled, empty bidsList (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { data: { offerCampaignBulkUpdateBids: { errors: [] } } } }; });
  const res = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "12", action: "resume" } });
  assert.equal(res.isError, false);
  assert.deepEqual(JSON.parse(seen[0].init.body).variables, { offerCmsId: "12", offerEnabled: true, bidsList: [] });
});
