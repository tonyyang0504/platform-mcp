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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/unity_ads.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_UNITY_ADS_KEY_ID: "unity-key", PLATFORM_MCP_UNITY_ADS_SECRET_KEY: "unity-secret-xyz", PLATFORM_MCP_UNITY_ADS_ORGANIZATION_ID: "org123", PLATFORM_MCP_UNITY_ADS_CAMPAIGN_SET_ID: "app1" });

test("unity_ads update_budget: org in base path, app from config, daily string (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { daily: "750.5", total: "0" } }; });
  const res = await client.callTool({ name: "update_budget", arguments: { campaign_id: "cmp1", daily_budget: 750.5 } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].init.method, "PATCH");
  assert.equal(seen[0].url.href, "https://services.api.unity.com/advertise/v1/organizations/org123/apps/app1/campaigns/cmp1/budget");
  assert.equal(seen[0].init.headers.Authorization, "Basic " + Buffer.from("unity-key:unity-secret-xyz").toString("base64"));
  assert.deepEqual(JSON.parse(seen[0].init.body), { daily: "750.5" });
});

test("unity_ads pause_resume: PATCH campaign enabled boolean (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { id: "cmp1", enabled: false } }; });
  const res = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "cmp1", action: "pause" } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].init.method, "PATCH");
  assert.equal(seen[0].url.href, "https://services.api.unity.com/advertise/v1/organizations/org123/apps/app1/campaigns/cmp1");
  assert.deepEqual(JSON.parse(seen[0].init.body), { enabled: false });
});
