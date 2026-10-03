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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/microsoft_advertising.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_MICROSOFT_ADVERTISING_CLIENT_ID: "4c0b-app", PLATFORM_MCP_MICROSOFT_ADVERTISING_REFRESH_TOKEN: "M.R3_rt", PLATFORM_MCP_MICROSOFT_ADVERTISING_DEVELOPER_TOKEN: "BBD37VB98", PLATFORM_MCP_MICROSOFT_ADVERTISING_CUSTOMER_ID: "21025739", PLATFORM_MCP_MICROSOFT_ADVERTISING_ACCOUNT_ID: "149082887" });

test("microsoft_advertising update_budget: public-client refresh with scope, DeveloperToken/CustomerId/CustomerAccountId headers, REST PUT (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.hostname === "login.microsoftonline.com") return { body: { access_token: "EwB", expires_in: 3599, token_type: "Bearer" } };
    return { body: { PartialErrors: [] } };
  });
  const res = await client.callTool({ name: "update_budget", arguments: { campaign_id: "804002", daily_budget: 40 } });
  assert.equal(res.isError, false);
  assert.deepEqual(form(seen[0].init.body), { grant_type: "refresh_token", refresh_token: "M.R3_rt", scope: "https://ads.microsoft.com/msads.manage", client_id: "4c0b-app" });
  assert.equal(seen[1].init.method, "PUT");
  assert.equal(seen[1].url.href, "https://campaign.api.bingads.microsoft.com/CampaignManagement/v13/Campaigns");
  const h = seen[1].init.headers;
  assert.equal(h.Authorization, "Bearer EwB"); assert.equal(h.DeveloperToken, "BBD37VB98"); assert.equal(h.CustomerId, "21025739"); assert.equal(h.CustomerAccountId, "149082887");
  assert.deepEqual(JSON.parse(seen[1].init.body), { AccountId: "149082887", Campaigns: [{ Id: "804002", DailyBudget: 40 }] });
  assert.equal(res.structuredContent.status, "updated");
  assert.deepEqual(res.structuredContent.partial_errors, []);
});

test("microsoft_advertising list_accounts searches the configured customer on the client center host (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.hostname === "login.microsoftonline.com") return { body: { access_token: "EwB", expires_in: 3599 } };
    return { body: { Accounts: [{ Id: "149082887", Name: "Acme US", CurrencyCode: "USDollar" }] } };
  });
  const res = await client.callTool({ name: "list_accounts", arguments: {} });
  assert.equal(seen[1].url.href, "https://clientcenter.api.bingads.microsoft.com/CustomerManagement/v13/Accounts/Search");
  assert.deepEqual(JSON.parse(seen[1].init.body), { Predicates: [{ Field: "CustomerId", Operator: "Equals", Value: "21025739" }], PageInfo: { Index: 0, Size: 100 } });
  assert.equal(res.structuredContent.accounts[0].name, "Acme US");
});

test("microsoft_advertising pause_resume sends Status Active for resume (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return url.hostname === "login.microsoftonline.com" ? { body: { access_token: "EwB", expires_in: 3599 } } : { body: { PartialErrors: [] } }; });
  const res = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "804002", action: "resume" } });
  assert.equal(res.isError, false);
  const put = seen.find((s) => s.init.method === "PUT");
  assert.deepEqual(JSON.parse(put.init.body), { AccountId: "149082887", Campaigns: [{ Id: "804002", Status: "Active" }] });
});
