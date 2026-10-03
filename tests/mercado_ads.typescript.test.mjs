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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/mercado_ads.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_MERCADO_ADS_CLIENT_ID: "mlcid", PLATFORM_MCP_MERCADO_ADS_CLIENT_SECRET: "mlsecret", PLATFORM_MCP_MERCADO_ADS_REFRESH_TOKEN: "TG-first" });

test("mercado_ads get_report: campaign metrics query with api-version 2 (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.pathname === "/oauth/token") return { body: { access_token: "APP_USR-1", expires_in: 21600, refresh_token: "TG-second" } };
    return { body: { paging: { total: 1 }, results: [{ id: 7, name: "A", currency_id: "MXN", metrics: { clicks: 10, prints: 900, cost: 55.5 } }] } };
  });
  const res = await client.callTool({ name: "get_report", arguments: { account_id: "111", date_from: "2026-07-01", date_to: "2026-07-31" } });
  assert.equal(res.isError, false);
  assert.equal(seen[1].url.pathname, "/advertising/advertisers/111/product_ads/campaigns");
  assert.equal(seen[1].url.searchParams.get("metrics"), "clicks,prints,ctr,cost,cpc,acos,units_quantity,total_amount");
  assert.equal(seen[1].url.searchParams.get("date_from"), "2026-07-01");
  assert.equal(seen[1].init.headers["Api-Version"], "2");
  assert.equal(res.structuredContent.rows[0].impressions, 900);
});
