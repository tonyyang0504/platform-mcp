import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (r.raw ?? JSON.stringify(r.body ?? {})) }; };
const form = (body) => Object.fromEntries(new URLSearchParams(body));
async function connect(spec, handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(spec);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/linkedin.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_LINKEDIN_CLIENT_ID: "86li", PLATFORM_MCP_LINKEDIN_CLIENT_SECRET: "lisecret", PLATFORM_MCP_LINKEDIN_REFRESH_TOKEN: "AQRrt", PLATFORM_MCP_LINKEDIN_AD_ACCOUNT_ID: "506333826" });

test("linkedin list_campaigns sends the version + Rest.li headers and the finder params (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.href === "https://www.linkedin.com/oauth/v2/accessToken") return { body: { access_token: "AQVat", expires_in: 5184000 } };
    return { body: { elements: [{ id: 186000001, name: "Q3 leads", status: "PAUSED", dailyBudget: { amount: "25", currencyCode: "USD" } }], metadata: {} } };
  });
  const res = await client.callTool({ name: "list_campaigns", arguments: { account_id: "506333826", status: "PAUSED" } });
  assert.equal(res.isError, false);
  assert.deepEqual(form(seen[0].init.body), { grant_type: "refresh_token", refresh_token: "AQRrt", client_id: "86li", client_secret: "lisecret" });
  const u = seen[1].url;
  assert.equal(u.pathname, "/rest/adAccounts/506333826/adCampaigns");
  assert.equal(u.searchParams.get("q"), "search"); assert.equal(u.searchParams.get("search.test"), "false"); assert.equal(u.searchParams.get("search.status.values[0]"), "PAUSED");
  assert.equal(seen[1].init.headers["Linkedin-Version"], "202609");
  assert.equal(seen[1].init.headers["X-Restli-Protocol-Version"], "2.0.0");
  assert.equal(seen[1].init.headers.Authorization, "Bearer AQVat");
  const c = res.structuredContent.campaigns[0];
  assert.equal(c.id, "186000001"); assert.equal(c.currency, "USD");
});

test("linkedin forbidden account is an auth_error (wire)", async () => {
  const client = await connect(SPEC, (url) => url.hostname === "www.linkedin.com" ? { body: { access_token: "AQVat", expires_in: 5184000 } } : { status: 403, body: { status: 403, message: "Not enough permissions to access: adAccounts" } });
  const res = await client.callTool({ name: "list_accounts", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.ok(!JSON.stringify(res.structuredContent).includes("lisecret"));
});

test("linkedin update_budget is a PARTIAL_UPDATE with a $set patch (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return url.hostname === "www.linkedin.com" ? { body: { access_token: "AQVat", expires_in: 5184000 } } : { status: 204, raw: "" }; });
  const res = await client.callTool({ name: "update_budget", arguments: { campaign_id: "186000001", daily_budget: 40, currency: "USD" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "updated");
  const req = seen.find((s) => s.url.pathname === "/rest/adAccounts/506333826/adCampaigns/186000001");
  assert.equal(req.init.method, "POST");
  assert.equal(req.init.headers["X-RestLi-Method"], "PARTIAL_UPDATE");
  assert.deepEqual(JSON.parse(req.init.body), { patch: { $set: { dailyBudget: { amount: "40", currencyCode: "USD" } } } });
  await client.callTool({ name: "pause_resume", arguments: { campaign_id: "186000001", action: "pause" } });
  assert.deepEqual(JSON.parse(seen.at(-1).init.body), { patch: { $set: { status: "PAUSED" } } });
});

test("linkedin get_report keeps Rest.li characters literal and the URN colons encoded (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push(url); return url.hostname === "www.linkedin.com" ? { body: { access_token: "AQVat", expires_in: 5184000 } } : { body: { elements: [{ pivotValues: ["urn:li:sponsoredCampaign:1"], dateRange: { start: { year: 2026, month: 9, day: 1 } }, impressions: 5 }] } }; });
  const res = await client.callTool({ name: "get_report", arguments: { account_id: "506333826", date_from: "2026-09-01", date_to: "2026-09-07" } });
  assert.equal(res.isError, false);
  const href = seen.at(-1).href;
  assert.ok(href.startsWith("https://api.linkedin.com/rest/adAnalytics?q=analytics&pivot=CAMPAIGN&timeGranularity=DAILY&"), href);
  assert.ok(href.includes("dateRange=(start:(year:2026,month:9,day:1),end:(year:2026,month:9,day:7))"), href);
  assert.ok(href.includes("accounts=List(urn%3Ali%3AsponsoredAccount%3A506333826)"), href);
  assert.equal(res.structuredContent.rows[0].impressions, 5);
});
