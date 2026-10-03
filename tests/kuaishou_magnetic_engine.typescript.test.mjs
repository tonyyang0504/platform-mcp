import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/kuaishou_magnetic_engine.json", import.meta.url), "utf8"));
const CREDS = { client_id: "74751", client_secret: "SECRET-ks", refresh_token: "REFRESH-ks-1", advertiser_id: "20000800" };

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

test("kuaishou_magnetic_engine: app_id/secret refresh, rotation, budget in 厘 and put_status", async () => {
  const log = [];
  const { client, t } = await connect((url) => (url.pathname.endsWith("/refresh_token")
    ? { code: 0, message: "OK", data: { access_token: "ACCESS-ks", access_token_expires_in: 86400, refresh_token: "REFRESH-ks-2" } }
    : { code: 0, message: "OK", data: {} }), log);
  const up = await client.callTool({ name: "update_budget", arguments: { campaign_id: "2342843", daily_budget: 600 } });
  assert.equal(up.isError, false);
  assert.deepEqual(JSON.parse(log[0].init.body), { refresh_token: "REFRESH-ks-1", app_id: "74751", secret: "SECRET-ks" });
  assert.equal(t.creds.refresh_token, "REFRESH-ks-2");
  assert.equal(log[1].init.headers["Access-Token"], "ACCESS-ks");
  assert.deepEqual(JSON.parse(log[1].init.body), { advertiser_id: 20000800, campaign_id: 2342843, day_budget: 600000 });
  await client.callTool({ name: "pause_resume", arguments: { campaign_id: "5", action: "resume" } });
  assert.deepEqual(JSON.parse(log[2].init.body), { advertiser_id: 20000800, campaign_id: 5, put_status: 1 });
});

test("kuaishou_magnetic_engine: non-zero code is an error", async () => {
  const log = [];
  const { client } = await connect((url) => (url.pathname.endsWith("/refresh_token") ? { code: 0, data: { access_token: "A", refresh_token: "R" } } : { code: 400002, message: "参数错误" }), log);
  const res = await client.callTool({ name: "list_campaigns", arguments: { account_id: "1" } });
  assert.equal(res.isError, true);
});
