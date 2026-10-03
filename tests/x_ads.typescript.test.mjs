import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/x_ads.json", import.meta.url), "utf8"));
const CREDS = { consumer_key: "CK-x", consumer_secret: "CS-x-secret", access_token: "AT-x", access_token_secret: "ATS-x-secret", account_id: "18ce54d4x5t" };
const enc = (s) => encodeURIComponent(String(s)).replace(/[!'()*]/g, (c) => "%" + c.charCodeAt(0).toString(16).toUpperCase());

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

test("x_ads: PUT campaign budget in micros with a valid OAuth 1.0a signature", async () => {
  const log = [];
  const c = await connect(() => ({ data: { id: "8wku2" } }), log);
  const res = await c.callTool({ name: "update_budget", arguments: { campaign_id: "8wku2", daily_budget: 5.5 } });
  assert.equal(res.isError, false);
  const { url, init } = log[0];
  assert.equal(init.method, "PUT");
  assert.equal(url.pathname, "/12/accounts/18ce54d4x5t/campaigns/8wku2");
  assert.equal(url.searchParams.get("daily_budget_amount_local_micro"), "5500000");
  const hdr = init.headers.Authorization;
  const oauth = Object.fromEntries(hdr.slice(6).split(", ").map((x) => { const [k, v] = x.split("="); return [k, decodeURIComponent(v.replace(/"/g, ""))]; }));
  const sig = oauth.oauth_signature; delete oauth.oauth_signature;
  const params = [...url.searchParams.entries(), ...Object.entries(oauth)].map(([k, v]) => [enc(k), enc(v)]).sort((a, b) => (a[0] === b[0] ? (a[1] < b[1] ? -1 : 1) : a[0] < b[0] ? -1 : 1));
  const base = ["PUT", enc(`${url.origin}${url.pathname}`), enc(params.map(([k, v]) => `${k}=${v}`).join("&"))].join("&");
  assert.equal(sig, crypto.createHmac("sha1", `${enc("CS-x-secret")}&${enc("ATS-x-secret")}`).update(base).digest("base64"));
});

test("x_ads: accounts cursor and stats query", async () => {
  const log = [];
  const c = await connect((url) => (url.pathname.startsWith("/12/stats") ? { data: [{ id: "8wku2", id_data: [] }] } : { next_cursor: "c-2", data: [{ id: "abc", name: "Acct" }] }), log);
  const acc = await c.callTool({ name: "list_accounts", arguments: {} });
  assert.equal(acc.structuredContent.next_cursor, "c-2");
  const rep = await c.callTool({ name: "get_report", arguments: { account_id: "abc", campaign_id: "8wku2", date_from: "2026-09-01", date_to: "2026-09-02" } });
  assert.equal(rep.isError, false);
  assert.equal(log[1].url.searchParams.get("metric_groups"), "ENGAGEMENT,BILLING");
  assert.equal(log[1].url.searchParams.get("entity_ids"), "8wku2");
});
