import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/lazada_sponsored_solutions.json", import.meta.url), "utf8"));
const CREDS = { app_key: "100001", app_secret: "SECRET-laz", refresh_token: "REFRESH-laz-1", api_domain: "api.lazada.sg" };
const hmacUp = (s) => crypto.createHmac("sha256", "SECRET-laz").update(s).digest("hex").toUpperCase();

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

test("lazada_sponsored_solutions: signed token refresh and signed API call without the /rest prefix", async () => {
  const log = [];
  const { client, t } = await connect((url) => (url.hostname === "auth.lazada.com"
    ? { access_token: "ACCESS-laz", refresh_token: "REFRESH-laz-2", expires_in: 604800, code: "0" }
    : { code: "0", success: "true", result: {} }), log);
  const res = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "101100024476086", action: "resume" } });
  assert.equal(res.isError, false);
  const tq = Object.fromEntries(log[0].url.searchParams.entries());
  assert.equal(log[0].url.pathname, "/rest/auth/token/refresh");
  assert.equal(tq.sign, hmacUp(`/auth/token/refreshapp_key100001refresh_tokenREFRESH-laz-1sign_methodsha256timestamp${tq.timestamp}`));
  assert.equal(t.creds.refresh_token, "REFRESH-laz-2");
  assert.equal(log[1].url.host, "api.lazada.sg");
  assert.equal(log[1].url.pathname, "/rest/sponsor/solutions/campaign/updateCampaign");
  const p = Object.fromEntries(log[1].url.searchParams.entries());
  const sig = p.sign; delete p.sign;
  assert.equal(p.access_token, "ACCESS-laz"); assert.equal(p.switchStatus, "1"); assert.equal(p.bizCode, "sponsoredSearch");
  assert.equal(sig, hmacUp("/sponsor/solutions/campaign/updateCampaign" + Object.keys(p).sort().map((k) => k + p[k]).join("")));
});

test("lazada_sponsored_solutions: gateway error code is an error", async () => {
  const log = [];
  const { client } = await connect((url) => (url.hostname === "auth.lazada.com" ? { access_token: "A", refresh_token: "R", expires_in: 604800 } : { type: "ISV", code: "IllegalAccessToken", message: "invalid" }), log);
  const res = await client.callTool({ name: "list_campaigns", arguments: { account_id: "shop" } });
  assert.equal(res.isError, true);
});
