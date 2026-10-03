import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/huawei_ads.json", import.meta.url), "utf8"));
const CREDS = { client_id: "10380742", client_secret: "SECRET-hw-1", refresh_token: "REFRESH-hw-1" };
const jsonResp = (status, body) => ({ status, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null) }, text: async () => JSON.stringify(body) });

async function connect(log, handler) {
  const a = SPEC.adapter;
  const f = async (url, init) => { log.push({ url, init }); return url.startsWith("https://oauth-login.cloud.huawei.com") ? jsonResp(200, { access_token: "ACCESS-hw-1", expires_in: 3600 }) : handler(url, init); };
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", f, a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("huawei_ads: campaign query is a GET with query parameters, no body (wire)", async () => {
  const log = [];
  const c = await connect(log, () => jsonResp(200, { code: "200", data: { total: 1, data: [{ campaign_id: "35002310", campaign_name: "C", today_daily_budget: "40" }] } }));
  const res = await c.callTool({ name: "list_campaigns", arguments: { account_id: "425985380605536128", limit: 20 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.campaigns[0].id, "35002310");
  const u = new URL(log[1].url);
  assert.equal(u.pathname, "/openapi/v2/promotion/campaign/query");
  assert.equal(u.searchParams.get("advertiser_id"), "425985380605536128"); assert.equal(u.searchParams.get("page_size"), "20");
  assert.equal(log[1].init.body, undefined);
  assert.equal(log[1].init.headers.Authorization, "Bearer ACCESS-hw-1");
});

test("huawei_ads: numeric and string 200 both succeed, other codes are errors", async () => {
  const log = [];
  const answers = [{ code: 200 }, { code: "200600", message: "daily budget unchanged" }];
  const c = await connect(log, () => jsonResp(200, answers.shift()));
  const ok = await c.callTool({ name: "pause_resume", arguments: { campaign_id: "30052950", action: "resume" } });
  assert.equal(ok.isError, false);
  assert.deepEqual(JSON.parse(log[1].init.body), { campaign_id: "30052950", campaign_status: "OPERATION_ENABLE" });
  const bad = await c.callTool({ name: "update_budget", arguments: { campaign_id: "30052950", daily_budget: 500 } });
  assert.equal(bad.isError, true);
});
