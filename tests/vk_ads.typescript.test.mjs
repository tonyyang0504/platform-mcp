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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/vk_ads.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_VK_ADS_CLIENT_ID: "vkcid", PLATFORM_MCP_VK_ADS_CLIENT_SECRET: "vksecret", PLATFORM_MCP_VK_ADS_REFRESH_TOKEN: "vkrefresh" });

test("vk_ads pause_resume: refresh grant then POST ad_plans/{id}.json (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.pathname === "/api/v2/oauth2/token.json") return { body: { access_token: "VKTOKEN", expires_in: "86400", refresh_token: "vkrefresh" } };
    return { status: 204, raw: "" };
  });
  const res = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "6617841", action: "resume" } });
  assert.equal(res.isError, false);
  assert.equal(form(seen[0].init.body).grant_type, "refresh_token");
  assert.equal(seen[1].init.method, "POST");
  assert.equal(seen[1].url.href, "https://ads.vk.ru/api/v2/ad_plans/6617841.json");
  assert.deepEqual(JSON.parse(seen[1].init.body), { status: "active" });
  assert.equal(res.structuredContent.status, "updated");
});
