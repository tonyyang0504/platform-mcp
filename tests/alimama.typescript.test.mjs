import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/alimama.json", import.meta.url), "utf8"));
const CREDS = { app_key: "12345678", app_secret: "SECRET-top", session: "SESSION-top", biz_code: "onebpDisplay" };

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
  const payload = "SECRET-top" + Object.keys(p).sort().map((k) => k + p[k]).join("") + "SECRET-top";
  assert.equal(sig, crypto.createHash("md5").update(payload).digest("hex").toUpperCase());
  return p;
}

test("alimama: TOP md5 signature with a GMT+8 timestamp and JSON-string parameters", async () => {
  const realNow = Date.now; Date.now = () => 1790301600000;
  try {
    const log = [];
    const c = await connect(() => ({ universalbp_new_campaign_budget_batchupdate_response: { top_result: { info: { ok: true } } } }), log);
    const res = await c.callTool({ name: "update_budget", arguments: { campaign_id: "68796878069", daily_budget: 99.5 } });
    assert.equal(res.isError, false);
    const p = verify(log[0].url);
    assert.equal(p.timestamp, "2026-09-25 10:00:00");
    assert.equal(p.method, "taobao.universalbp.new.campaign.budget.batchupdate");
    assert.deepEqual(JSON.parse(p.top_service_context), { biz_code: "onebpDisplay" });
    assert.deepEqual(JSON.parse(p.campaign_budget_list_v_o), { budget_list: [{ campaign_id: 68796878069, dmc_type: "normal", day_budget: 99.5 }] });
  } finally { Date.now = realNow; }
});

test("alimama: error_response is an error; pause maps to oneclick", async () => {
  const log = [];
  const c = await connect(() => ({ error_response: { code: 50, msg: "Remote service error", sub_msg: "非法参数" } }), log);
  const res = await c.callTool({ name: "pause_resume", arguments: { campaign_id: "1", action: "pause" } });
  assert.equal(res.isError, true);
  const p = verify(log[0].url);
  assert.equal(p.method, "taobao.universalbp.new.campaign.oneclick");
  assert.deepEqual(JSON.parse(p.one_click_v_o), { campaign_id_list: [1] });
});
