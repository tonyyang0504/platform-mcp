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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/google.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_GOOGLE_CLIENT_ID: "cid", PLATFORM_MCP_GOOGLE_CLIENT_SECRET: "gsecret", PLATFORM_MCP_GOOGLE_REFRESH_TOKEN: "1//rt", PLATFORM_MCP_GOOGLE_DEVELOPER_TOKEN: "devtok", PLATFORM_MCP_GOOGLE_CUSTOMER_ID: "1234567890", PLATFORM_MCP_GOOGLE_LOGIN_CUSTOMER_ID: "9998887777" });

test("google_ads list_campaigns mints from the refresh token and sends developer-token + login-customer-id (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.href === "https://oauth2.googleapis.com/token") return { body: { access_token: "ya29.A", expires_in: 3599 } };
    return { body: { results: [{ campaign: { id: "42", name: "Brand", status: "PAUSED", startDateTime: "2026-01-01 00:00:00" }, campaignBudget: { amountMicros: "50000000" } }] } };
  });
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_report", "list_accounts", "list_campaigns", "me", "pause_resume"]);
  const res = await client.callTool({ name: "list_campaigns", arguments: { account_id: "5550001111" } });
  assert.equal(res.isError, false);
  assert.deepEqual(form(seen[0].init.body), { grant_type: "refresh_token", refresh_token: "1//rt", client_id: "cid", client_secret: "gsecret" });
  assert.equal(seen[1].url.href, "https://googleads.googleapis.com/v25/customers/5550001111/googleAds:search");
  assert.equal(seen[1].init.method, "POST");
  assert.equal(seen[1].init.headers.Authorization, "Bearer ya29.A");
  assert.equal(seen[1].init.headers["developer-token"], "devtok");
  assert.equal(seen[1].init.headers["login-customer-id"], "9998887777");
  assert.match(JSON.parse(seen[1].init.body).query, /^SELECT campaign\.id, campaign\.name/);
  const c = res.structuredContent.campaigns[0];
  assert.equal(c.id, "42"); assert.equal(c.status, "PAUSED"); assert.equal(c.start, "2026-01-01 00:00:00");
});

test("google_ads revoked refresh token is an auth_error without secrets (wire)", async () => {
  const client = await connect(SPEC, () => ({ status: 400, body: { error: "invalid_grant" } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.ok(!JSON.stringify(res.structuredContent).includes("gsecret"));
});

test("google_ads pause_resume composes the resource name and sets updateMask (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return url.hostname === "oauth2.googleapis.com" ? { body: { access_token: "ya29.A", expires_in: 3599 } } : { body: { results: [{ resourceName: "customers/1234567890/campaigns/42" }] } }; });
  const res = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "42", action: "resume" } });
  assert.equal(res.isError, false);
  const req = seen.find((s) => s.url.pathname.endsWith("campaigns:mutate"));
  assert.equal(req.url.href, "https://googleads.googleapis.com/v25/customers/1234567890/campaigns:mutate");
  assert.deepEqual(JSON.parse(req.init.body), { operations: [{ update: { resourceName: "customers/1234567890/campaigns/42", status: "ENABLED" }, updateMask: "status" }] });
});

test("google_ads get_report splices the dates into GAQL (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return url.hostname === "oauth2.googleapis.com" ? { body: { access_token: "ya29.A", expires_in: 3599 } } : { body: { results: [{ campaign: { id: "42" }, segments: { date: "2026-09-01" }, metrics: { costMicros: "12500000" } }] } }; });
  const res = await client.callTool({ name: "get_report", arguments: { account_id: "5550001111", date_from: "2026-09-01", date_to: "2026-09-07" } });
  assert.equal(res.structuredContent.rows[0].cost_micros, "12500000");
  assert.match(JSON.parse(seen.at(-1).init.body).query, /BETWEEN '2026-09-01' AND '2026-09-07'/);
});
