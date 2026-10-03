import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/baidu_marketing.json", import.meta.url), "utf8"));
const CREDS = { client_id: "APPID-bd-1", client_secret: "SECRET-bd-1", refresh_token: "REFRESH-bd-1", user_id: "630152", user_name: "shop-sem" };
const jsonResp = (status, body) => ({ status, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null) }, text: async () => JSON.stringify(body) });
const OK = { status: 0, desc: "success", failures: [] };

async function connect(log, handler) {
  const a = SPEC.adapter;
  const f = async (url, init) => { log.push({ url, init }); return url.includes("u.baidu.com/oauth/refreshToken") ? jsonResp(200, { code: 0, data: { accessToken: "ACCESS-bd-1", refreshToken: "REFRESH-bd-2", expiresIn: 86400 } }) : handler(url, init); };
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", f, a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("baidu_marketing: refresh grant with Baidu field names and the token in header.accessToken (wire)", async () => {
  const log = [];
  const c = await connect(log, () => jsonResp(200, { header: OK, body: { data: [{ campaignId: 86415412, campaignName: "测试计划", budget: 50, pause: false }] } }));
  const res = await c.callTool({ name: "list_campaigns", arguments: { account_id: "sub-2" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.campaigns[0].id, "86415412");
  assert.deepEqual(JSON.parse(log[0].init.body), { refreshToken: "REFRESH-bd-1", appId: "APPID-bd-1", secretKey: "SECRET-bd-1", userId: 630152 });
  const body = JSON.parse(log[1].init.body);
  assert.equal(log[1].url, "https://api.baidu.com/json/sms/service/CampaignService/getCampaign");
  assert.deepEqual(body.header, { userName: "sub-2", accessToken: "ACCESS-bd-1" });
  assert.equal(log[1].init.headers.Authorization, undefined);
});

test("baidu_marketing: pause via updateCampaign", async () => {
  const log = [];
  const c = await connect(log, () => jsonResp(200, { header: OK, body: { data: [{ campaignId: 86415412, pause: true }] } }));
  const res = await c.callTool({ name: "pause_resume", arguments: { campaign_id: "86415412", action: "pause" } });
  assert.equal(res.structuredContent.status, "updated");
  const body = JSON.parse(log[1].init.body);
  assert.deepEqual(body, { header: { userName: "shop-sem", accessToken: "ACCESS-bd-1" }, body: { campaignTypes: [{ campaignId: 86415412, pause: true }] } });
});
