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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/reddit.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_REDDIT_CLIENT_ID: "rdcid", PLATFORM_MCP_REDDIT_CLIENT_SECRET: "rdsecret", PLATFORM_MCP_REDDIT_REFRESH_TOKEN: "rd-refresh-1", PLATFORM_MCP_REDDIT_BUSINESS_ID: "biz9" });

test("reddit (ads) get_report: refresh with basic auth, report body (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.hostname === "www.reddit.com") return { body: { access_token: "RDTOKEN1", expires_in: 3600 } };
    return { body: { data: { metrics: [{ campaign_id: "c1", date: "2026-09-01", impressions: 10, spend: 5000000 }] } } };
  });
  const res = await client.callTool({ name: "get_report", arguments: { account_id: "t2_abc", date_from: "2026-09-01", date_to: "2026-09-02" } });
  assert.equal(res.isError, false);
  assert.match(seen[0].init.headers.Authorization, /^Basic /);
  assert.equal(seen[1].url.href, "https://ads-api.reddit.com/api/v3/ad_accounts/t2_abc/reports");
  assert.equal(JSON.parse(seen[1].init.body).data.starts_at, "2026-09-01T00:00:00Z");
  assert.equal(res.structuredContent.rows[0].spend_micros, 5000000);
});
