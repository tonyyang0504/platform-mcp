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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/mgid.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_MGID_API_TOKEN: "mgid0123456789abcdef0123456789ab", PLATFORM_MCP_MGID_CLIENT_ID: "555" });

test("mgid update_budget: PATCH with query parameters and client path (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { id: 777 } }; });
  const res = await client.callTool({ name: "update_budget", arguments: { campaign_id: "777", daily_budget: 25.5 } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].init.method, "PATCH");
  assert.equal(seen[0].url.pathname, "/v1/goodhits/clients/555/campaigns/777");
  assert.equal(seen[0].url.searchParams.get("limitType"), "budget_limits");
  assert.equal(seen[0].url.searchParams.get("dailyLimit"), "25.5");
  assert.equal(seen[0].init.headers.Authorization, "Bearer mgid0123456789abcdef0123456789ab");
  assert.equal(res.structuredContent.status, "updated");
});
