import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/jd_jzt.json", import.meta.url), "utf8"));
const CREDS = { app_key: "APPKEY-jd", app_secret: "SECRET-jd", access_token: "TOKEN-jd" };

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

function verify(url) {
  const p = Object.fromEntries(url.searchParams.entries());
  const sig = p.sign; delete p.sign;
  assert.equal(sig, crypto.createHash("md5").update("SECRET-jd" + Object.keys(p).sort().map((k) => k + p[k]).join("") + "SECRET-jd").digest("hex").toUpperCase());
  return p;
}

test("jd_jzt: JOS signature, GMT+8 timestamp and 360buy_param_json for status updates", async () => {
  const realNow = Date.now; Date.now = () => 1790301600000;
  try {
    const log = [];
    const c = await connect(() => ({ jingdong_ads_dsp_rtb_kuaiche_campaign_updatestatus_v2_responce: { data: { code: "1", success: true, data: 1 } } }), log);
    const res = await c.callTool({ name: "pause_resume", arguments: { campaign_id: "111", action: "resume" } });
    assert.equal(res.isError, false);
    const p = verify(log[0].url);
    assert.equal(p.timestamp, "2026-09-25 10:00:00");
    assert.equal(p.method, "jingdong.ads.dsp.rtb.kuaiche.campaign.updatestatus.v2");
    assert.deepEqual(JSON.parse(p["360buy_param_json"]), { data: { ids: [111], operateType: 2 }, system: {} });
  } finally { Date.now = realNow; }
});

test("jd_jzt: campaign rows under item and gateway errors", async () => {
  const log = [];
  let n = 0;
  const c = await connect(() => (n++ === 0
    ? { jingdong_ads_dsp_rtb_kuaiche_campaign_list_v2_responce: { data: { code: "1", success: true, data: { paginator: { items: 1 }, datas: [{ item: { campaignId: "111", campaignName: "c", status: "1" } }] } } } }
    : { error_response: { code: "19", zh_desc: "token过期" } }), log);
  const list = await c.callTool({ name: "list_campaigns", arguments: { account_id: "pin" } });
  assert.equal(list.structuredContent.campaigns[0].id, "111");
  const bad = await c.callTool({ name: "update_budget", arguments: { campaign_id: "111", daily_budget: 100 } });
  assert.equal(bad.isError, true);
  assert.deepEqual(JSON.parse(verify(log[1].url)["360buy_param_json"]), { data: { id: 111, dayBudget: 100 }, system: { platformBusinessType: "DST_JZT" } });
});
