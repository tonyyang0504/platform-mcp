import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/xiaohongshu_pugongying.json", import.meta.url), "utf8"));
const CREDS = { client_id: "1", client_secret: "SECRET-xhs", refresh_token: "REFRESH-xhs-1", advertiser_id: "1234" };

async function connect(handler, log) {
  const f = async (url, init) => { log.push({ url: new URL(url), init }); return { status: 200, headers: { get: () => "application/json" }, text: async () => JSON.stringify(handler(new URL(url), init)) }; };
  const a = SPEC.adapter;
  const t = new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", f, a.envelope ?? {});
  const server = buildServer(SPEC, t);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return { client, t };
}

test("xiaohongshu_pugongying: app_id/secret refresh with nested rotation; budget in 分; pause action_type", async () => {
  const log = [];
  const { client, t } = await connect((url) => (url.pathname.endsWith("/oauth2/refresh_token")
    ? { code: 0, success: true, data: { access_token: "ACCESS-xhs", access_token_expires_in: 86399, refresh_token: "REFRESH-xhs-2" } }
    : { code: 0, success: true, data: {} }), log);
  assert.equal((await client.callTool({ name: "update_budget", arguments: { campaign_id: "9876", daily_budget: 150 } })).isError, false);
  assert.deepEqual(JSON.parse(log[0].init.body), { refresh_token: "REFRESH-xhs-1", app_id: "1", secret: "SECRET-xhs" });
  assert.equal(t.creds.refresh_token, "REFRESH-xhs-2");
  assert.equal(log[1].init.headers["Access-Token"], "ACCESS-xhs");
  assert.deepEqual(JSON.parse(log[1].init.body), { advertiser_id: 1234, campaign_id: 9876, limit_day_budget: 1, campaign_day_budget: 15000 });
  assert.equal((await client.callTool({ name: "pause_resume", arguments: { campaign_id: "9876", action: "resume" } })).isError, false);
  assert.deepEqual(JSON.parse(log[2].init.body), { advertiser_id: 1234, campaign_ids: [9876], action_type: 1 });
});

test("xiaohongshu_pugongying: non-zero code is an error", async () => {
  const log = [];
  const { client } = await connect((url) => (url.pathname.endsWith("/oauth2/refresh_token") ? { code: 0, data: { access_token: "A", refresh_token: "R" } } : { code: 10001, success: false, msg: "参数错误" }), log);
  assert.equal((await client.callTool({ name: "list_campaigns", arguments: { account_id: "1234" } })).isError, true);
});
