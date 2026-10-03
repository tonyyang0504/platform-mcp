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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/yandex_direct.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_YANDEX_DIRECT_TOKEN: "y0_yandextoken", PLATFORM_MCP_YANDEX_DIRECT_CLIENT_LOGIN: "client-login" });

test("yandex_direct list_campaigns: JSON-RPC style body and error-object envelope (wire)", async () => {
  const seen = [];
  let call = 0;
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    call += 1;
    if (call === 1) return { body: { result: { Campaigns: [{ Id: 101, Name: "Search RU", State: "ON", DailyBudget: { Amount: 500000000 } }] } } };
    return { body: { error: { error_code: 53, error_string: "Authorization error" } } };
  });
  const res = await client.callTool({ name: "list_campaigns", arguments: { account_id: "x", status: "ON" } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].url.href, "https://api.direct.yandex.com/json/v5/campaigns");
  assert.equal(seen[0].init.headers["Client-Login"], "client-login");
  const body = JSON.parse(seen[0].init.body);
  assert.equal(body.method, "get");
  assert.deepEqual(body.params.SelectionCriteria, { States: ["ON"] });
  assert.equal(res.structuredContent.campaigns[0].budget_micros, 500000000);
  const bad = await client.callTool({ name: "me", arguments: {} });
  assert.equal(bad.isError, true);
});
