import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/ocean_engine.json", import.meta.url), "utf8"));
const CREDS = { client_id: "1700000000", client_secret: "SECRET-oe", refresh_token: "REFRESH-oe-1", advertiser_id: "4242" };

async function connect(handler, log, creds = CREDS) {
  const f = async (url, init) => { log.push({ url: new URL(url), init }); return { status: 200, headers: { get: () => "application/json" }, text: async () => JSON.stringify(handler(new URL(url), init)) }; };
  const a = SPEC.adapter;
  const t = new Transport(a.base_url, a.auth, { ...creds }, 50, "test", f, a.envelope ?? {});
  const server = buildServer(SPEC, t);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return { client, t };
}

const handler = (url) => {
  if (url.pathname.endsWith("/oauth2/refresh_token/")) return { code: 0, message: "OK", data: { access_token: "ACCESS-oe", refresh_token: "REFRESH-oe-2", expires_in: 86400 } };
  if (url.pathname.endsWith("/oauth2/advertiser/get/")) return { code: 0, message: "OK", data: { list: [{ advertiser_id: 4242, advertiser_name: "A" }] } };
  return { code: 0, message: "OK", data: { project_ids: [77] } };
};

test("ocean_engine: app_id/secret refresh, nested rotation, token as query only for list_accounts", async () => {
  const log = [];
  const { client, t } = await connect(handler, log);
  const acc = await client.callTool({ name: "list_accounts", arguments: {} });
  assert.equal(acc.isError, false);
  assert.equal(acc.structuredContent.accounts[0].id, "4242");
  assert.deepEqual(JSON.parse(log[0].init.body), { refresh_token: "REFRESH-oe-1", app_id: "1700000000", secret: "SECRET-oe" });
  assert.equal(t.creds.refresh_token, "REFRESH-oe-2");
  assert.equal(log[1].url.searchParams.get("access_token"), "ACCESS-oe");
  const up = await client.callTool({ name: "update_budget", arguments: { campaign_id: "77", daily_budget: 300 } });
  assert.equal(up.isError, false);
  assert.equal(log[2].url.searchParams.get("access_token"), null);
  assert.equal(log[2].init.headers["Access-Token"], "ACCESS-oe");
  assert.deepEqual(JSON.parse(log[2].init.body), { advertiser_id: 4242, data: [{ project_id: 77, budget_mode: "BUDGET_MODE_DAY", budget: 300 }] });
});

test("ocean_engine: code != 0 is an error; report window formatting", async () => {
  const log = [];
  const { client } = await connect((url) => (url.pathname.includes("/report/") ? { code: 40002, message: "No permission", data: {} } : handler(url)), log);
  const rep = await client.callTool({ name: "get_report", arguments: { account_id: "4242", date_from: "2026-09-01", date_to: "2026-09-02" } });
  assert.equal(rep.isError, true);
  const q = log[1].url.searchParams;
  assert.equal(q.get("start_time"), "2026-09-01 00:00:00");
  assert.equal(q.get("end_time"), "2026-09-02 23:59:59");
});
