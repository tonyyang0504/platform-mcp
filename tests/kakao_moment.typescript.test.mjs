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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/kakao_moment.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_KAKAO_MOMENT_BUSINESS_TOKEN: "KMOMTOKEN", PLATFORM_MCP_KAKAO_MOMENT_AD_ACCOUNT_ID: "10000" });

test("kakao_moment pause_resume: PUT onOff {id, config} (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { raw: "" }; });
  const res = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "5678", action: "pause" } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].init.method, "PUT");
  assert.equal(seen[0].url.href, "https://apis.moment.kakao.com/openapi/v4/campaigns/onOff");
  assert.equal(seen[0].init.headers.adAccountId, "10000");
  assert.deepEqual(JSON.parse(seen[0].init.body), { id: 5678, config: "OFF" });
});
