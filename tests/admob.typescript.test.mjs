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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/admob.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_ADMOB_CLIENT_ID: "gcid", PLATFORM_MCP_ADMOB_CLIENT_SECRET: "gsecret", PLATFORM_MCP_ADMOB_REFRESH_TOKEN: "1//admobrefresh" });

test("admob get_report: reportSpec date parts, streamed array without header/footer (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.hostname === "oauth2.googleapis.com") return { body: { access_token: "ya29.AM", expires_in: 3599 } };
    return { body: [{ header: {} }, { row: { dimensionValues: { DATE: { value: "20260901" } }, metricValues: { IMPRESSIONS: { integerValue: "10" } } } }, { footer: { matchingRowCount: "1" } }] };
  });
  const res = await client.callTool({ name: "get_report", arguments: { account_id: "pub-1", date_from: "2026-09-01", date_to: "2026-09-30" } });
  assert.equal(res.isError, false);
  assert.equal(form(seen[0].init.body).grant_type, "refresh_token");
  assert.equal(seen[1].url.href, "https://admob.googleapis.com/v1/accounts/pub-1/networkReport:generate");
  assert.deepEqual(JSON.parse(seen[1].init.body).reportSpec.dateRange, { startDate: { year: 2026, month: 9, day: 1 }, endDate: { year: 2026, month: 9, day: 30 } });
  assert.equal(res.structuredContent.rows.length, 1);
  assert.equal(res.structuredContent.rows[0].impressions, "10");
});
