import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (r.raw ?? JSON.stringify(r.body ?? {})) }; };
async function connect(spec, handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(spec);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/avito_ads.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_AVITO_ADS_CLIENT_ID: "av-cid", PLATFORM_MCP_AVITO_ADS_CLIENT_SECRET: "av-secret-xyz", PLATFORM_MCP_AVITO_ADS_ACCOUNT_ID: "4242" });

test("avito_ads me: token then GET account path from config (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.pathname === "/token") return { body: { access_token: "AVT", expires_in: 86400 } };
    return { body: { inn: "7700000000", shortName: "ООО Тест" } };
  });
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, false);
  assert.equal(seen[1].url.href, "https://api.avito.ru/ads/v1/account/4242");
  assert.equal(seen[1].init.headers.Authorization, "Bearer AVT");
});

test("avito_ads list_campaigns: filter object without status (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.pathname === "/token") return { body: { access_token: "AVT", expires_in: 86400 } };
    return { body: { total: 0, campaigns: [] } };
  });
  await client.callTool({ name: "list_campaigns", arguments: { account_id: "4242" } });
  assert.deepEqual(JSON.parse(seen[1].init.body), { filter: {}, limit: 20, page: 1 });
});
