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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/dv360.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_DV360_CLIENT_ID: "gcid", PLATFORM_MCP_DV360_CLIENT_SECRET: "gsecret", PLATFORM_MCP_DV360_REFRESH_TOKEN: "1//dvrefresh", PLATFORM_MCP_DV360_PARTNER_ID: "123", PLATFORM_MCP_DV360_ADVERTISER_ID: "456" });

test("dv360 pause_resume: PATCH with updateMask and advertiser from config (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.hostname === "oauth2.googleapis.com") return { body: { access_token: "ya29.DV", expires_in: 3599 } };
    return { body: { campaignId: "9", entityStatus: "ENTITY_STATUS_ACTIVE" } };
  });
  const res = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "9", action: "resume" } });
  assert.equal(res.isError, false);
  assert.equal(form(seen[0].init.body).refresh_token, "1//dvrefresh");
  assert.equal(seen[1].init.method, "PATCH");
  assert.equal(seen[1].url.pathname, "/v4/advertisers/456/campaigns/9");
  assert.equal(seen[1].url.searchParams.get("updateMask"), "entityStatus");
  assert.deepEqual(JSON.parse(seen[1].init.body), { entityStatus: "ENTITY_STATUS_ACTIVE" });
  assert.equal(res.structuredContent.status, "ENTITY_STATUS_ACTIVE");
});
