import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/mintegral.json", import.meta.url), "utf8"));
const CREDS = { access_key: "AK-mtg-1", api_key: "APIKEY-mtg-secret" };
const fakeFetch = (log, handler) => async (url, init) => { log.push({ url: new URL(url), init }); const r = handler(new URL(url), init); return { status: 200, headers: { get: () => "application/json" }, text: async () => JSON.stringify(r) }; };

async function connect(handler, log = []) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", fakeFetch(log, handler), a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("mintegral: token header = md5(api_key + md5(timestamp)) and offers listed as campaigns", async () => {
  const realNow = Date.now; Date.now = () => 1790301600000;
  try {
    const log = [];
    const c = await connect(() => ({ code: 200, msg: "success", data: { total: 3, list: [{ offer_id: 10010, offer_name: "o1", status: "RUNNING", currency: "USD" }] } }), log);
    const res = await c.callTool({ name: "list_campaigns", arguments: { account_id: "1", page: 1, limit: 10 } });
    assert.equal(res.isError, false);
    assert.equal(res.structuredContent.campaigns[0].id, "10010");
    assert.equal(log[0].url.pathname, "/api/open/v1/offers");
    assert.equal(log[0].url.searchParams.get("limit"), "10");
    const h = log[0].init.headers;
    assert.equal(h["access-key"], "AK-mtg-1");
    assert.equal(h.timestamp, "1790301600");
    const inner = crypto.createHash("md5").update("1790301600").digest("hex");
    assert.equal(h.token, crypto.createHash("md5").update("APIKEY-mtg-secret" + inner).digest("hex"));
  } finally { Date.now = realNow; }
});

test("mintegral: budget body and code != 200 is an error", async () => {
  const log = [];
  const c = await connect((url) => (url.pathname.endsWith("/offer/status") ? { code: 10000, msg: "error", data: {} } : { code: 200, msg: "success", data: {} }), log);
  const ok = await c.callTool({ name: "update_budget", arguments: { campaign_id: "123", daily_budget: 80 } });
  assert.equal(ok.isError, false);
  assert.equal(log[0].init.method, "PUT");
  assert.deepEqual(JSON.parse(log[0].init.body), { offer_id: 123, budget: [{ country_code: "ALL", daily_cap_type: "BUDGET", daily_cap: 80, total_budget: "OPEN" }] });
  const bad = await c.callTool({ name: "pause_resume", arguments: { campaign_id: "123", action: "resume" } });
  assert.equal(bad.isError, true);
  assert.deepEqual(JSON.parse(log[1].init.body), { offer_id: 123, status: "RUNNING" });
});
