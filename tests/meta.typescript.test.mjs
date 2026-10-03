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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/meta.json", import.meta.url), "utf8"));
process.env.PLATFORM_MCP_META_ACCESS_TOKEN = "EAAGtok";

test("meta update_budget posts an integer daily_budget to the campaign node with the bearer (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { success: true } }; });
  const res = await client.callTool({ name: "update_budget", arguments: { campaign_id: "120200", daily_budget: 5000 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "updated");
  assert.equal(seen[0].url.href, "https://graph.facebook.com/v26.0/120200");
  assert.equal(seen[0].init.method, "POST");
  assert.equal(seen[0].init.headers.Authorization, "Bearer EAAGtok");
  assert.deepEqual(JSON.parse(seen[0].init.body), { daily_budget: 5000 });
  const bad = await client.callTool({ name: "update_budget", arguments: { campaign_id: "120200", daily_budget: 12.5 } });
  assert.equal(bad.isError, true);
  assert.equal(bad.structuredContent.error, "invalid_input");
});

test("meta list_campaigns maps data rows and the summary total (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url) => { seen.push(url); return { body: { data: [{ id: "1", name: "Spring", status: "ACTIVE", start_time: "2026-03-01T00:00:00+0000" }], summary: { total_count: 1 } } }; });
  const res = await client.callTool({ name: "list_campaigns", arguments: { account_id: "act_1010" } });
  assert.equal(seen[0].pathname, "/v26.0/act_1010/campaigns");
  assert.equal(seen[0].searchParams.get("summary"), "total_count");
  assert.equal(res.structuredContent.campaigns[0].name, "Spring");
  assert.equal(res.structuredContent.total, 1);
});

test("meta pause_resume maps pause to PAUSED (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { success: true } }; });
  const res = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "120200", action: "pause" } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].url.href, "https://graph.facebook.com/v26.0/120200");
  assert.deepEqual(JSON.parse(seen[0].init.body), { status: "PAUSED" });
});
