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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/qihoo_360_ads.json", import.meta.url), "utf8"));
const ENC = "9f".repeat(32);
Object.assign(process.env, { PLATFORM_MCP_QIHOO_360_ADS_API_KEY: "APIKEY-360", PLATFORM_MCP_QIHOO_360_ADS_USERNAME: "dj-user", PLATFORM_MCP_QIHOO_360_ADS_ENCRYPTED_PASSWORD: ENC });

test("qihoo_360_ads clientLogin is a form POST with the apiKey header; calls carry apiKey + accessToken (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return url.pathname === "/uc/account/clientLogin" ? { body: { uid: "1", accessToken: "ACCESS-360" } } : { body: { uid: "160185657", userName: "测试" } }; });
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, false);
  assert.equal(seen[0].init.headers.apiKey, "APIKEY-360");
  assert.deepEqual(Object.fromEntries(new URLSearchParams(seen[0].init.body)), { username: "dj-user", passwd: ENC });
  assert.equal(seen[1].url.pathname, "/uc/account/getInfo");
  assert.equal(seen[1].init.headers.apiKey, "APIKEY-360");
  assert.equal(seen[1].init.headers.accessToken, "ACCESS-360");
});

test("qihoo_360_ads campaign/update form bodies and failures[] envelope (wire)", async () => {
  const seen = []; let n = 0;
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); if (url.pathname.endsWith("clientLogin")) return { body: { accessToken: "ACCESS-360" } }; n += 1;
    return { body: n < 3 ? { id: "3907501127" } : { affectedRecords: [], failures: [{ code: 30503, message: "推广计划每日预算格式不正确" }] } }; });
  const ok = await client.callTool({ name: "update_budget", arguments: { campaign_id: "3907501127", daily_budget: 230 } });
  assert.equal(ok.isError, false);
  assert.deepEqual(Object.fromEntries(new URLSearchParams(seen[1].init.body)), { id: "3907501127", budget: "230" });
  await client.callTool({ name: "pause_resume", arguments: { campaign_id: "3907501127", action: "pause" } });
  assert.deepEqual(Object.fromEntries(new URLSearchParams(seen[2].init.body)), { id: "3907501127", status: "pause" });
  const bad = await client.callTool({ name: "update_budget", arguments: { campaign_id: "3907501127", daily_budget: 10 } });
  assert.equal(bad.isError, true);
});
