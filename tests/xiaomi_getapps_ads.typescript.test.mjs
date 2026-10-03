import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/xiaomi_getapps_ads.json", import.meta.url), "utf8"));
const CREDS = { app_id: "wmsj", app_key: "APPKEY-mi-secret" };

async function connect(handler, log) {
  const f = async (url, init) => { log.push({ url: new URL(url), init }); return { status: 200, headers: { get: () => "application/json" }, text: async () => JSON.stringify(handler(new URL(url), init)) }; };
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", f, a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("xiaomi_getapps_ads: createToken login, cookie-borne access_token/timestamp/uid, group budget", async () => {
  const log = [];
  const c = await connect((url) => (url.pathname.endsWith("/createToken")
    ? { code: 0, message: "成功", result: { accessToken: "ACCESS-mi", expireDate: "2026-09-25T10:28:04.570Z" } }
    : url.pathname.endsWith("/campaign/list") ? { code: 0, result: { total: 1, records: [{ campaignId: 7, name: "c" }] } } : { code: 0, message: "成功" }), log);
  const list = await c.callTool({ name: "list_campaigns", arguments: { account_id: "1420" } });
  assert.equal(list.isError, false);
  assert.equal(list.structuredContent.campaigns[0].id, "7");
  assert.deepEqual(JSON.parse(log[0].init.body), { appId: "wmsj", appKey: "APPKEY-mi-secret" });
  assert.match(log[1].init.headers.Cookie, /^access_token=ACCESS-mi; timestamp=\d{13}; uid=[0-9a-f]{32}$/);
  assert.equal(log[1].init.headers.Authorization, undefined);
  assert.equal(log[1].url.searchParams.get("accountIds"), "1420");
  const up = await c.callTool({ name: "update_budget", arguments: { campaign_id: "32434", daily_budget: 5 } });
  assert.equal(up.isError, false);
  assert.deepEqual(JSON.parse(log[2].init.body), { groupIds: [32434], dayBudget: 500000 });
});
