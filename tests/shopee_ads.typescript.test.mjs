import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/shopee_ads.json", import.meta.url), "utf8"));
const CREDS = { partner_id: "1001", shop_id: "2002", partner_key: "PKEY-shopee-secret", refresh_token: "REFRESH-sa-1" };

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

test("shopee_ads: signed refresh, minted token inside every call's signature, pause edit_action", async () => {
  const realNow = Date.now; Date.now = () => 1790301600000;
  try {
    const log = [];
    const c = await connect((url) => (url.pathname.endsWith("/access_token/get")
      ? { error: "", access_token: "ACCESS-sa", refresh_token: "REFRESH-sa-2", expire_in: 14400 }
      : { error: "", message: "", response: [{ campaign_id: 112234 }] }), log);
    const res = await c.callTool({ name: "pause_resume", arguments: { campaign_id: "112234", action: "pause" } });
    assert.equal(res.isError, false);
    assert.deepEqual(JSON.parse(log[0].init.body), { refresh_token: "REFRESH-sa-1", partner_id: 1001, shop_id: 2002 });
    assert.equal(log[0].url.searchParams.get("sign"), crypto.createHmac("sha256", "PKEY-shopee-secret").update("1001/api/v2/auth/access_token/get1790301600").digest("hex"));
    const q = log[1].url.searchParams;
    assert.equal(log[1].url.pathname, "/api/v2/ads/edit_manual_product_ads");
    assert.equal(q.get("access_token"), "ACCESS-sa");
    assert.equal(q.get("sign"), crypto.createHmac("sha256", "PKEY-shopee-secret").update("1001/api/v2/ads/edit_manual_product_ads1790301600ACCESS-sa2002").digest("hex"));
    const body = JSON.parse(log[1].init.body);
    assert.equal(body.edit_action, "pause"); assert.equal(body.campaign_id, 112234);
  } finally { Date.now = realNow; }
});

test("shopee_ads: error field is an error; report dates as DD-MM-YYYY", async () => {
  const log = [];
  const c = await connect((url) => (url.pathname.endsWith("/access_token/get") ? { error: "", access_token: "A", refresh_token: "R", expire_in: 14400 } : { error: "error_param", message: "Wrong parameters." }), log);
  const rep = await c.callTool({ name: "get_report", arguments: { account_id: "2002", date_from: "2021-03-17", date_to: "2021-03-18" } });
  assert.equal(rep.isError, true);
  assert.equal(log[1].url.searchParams.get("start_date"), "17-03-2021");
});
