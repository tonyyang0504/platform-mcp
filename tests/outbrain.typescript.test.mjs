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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/outbrain.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_OUTBRAIN_OB_TOKEN: "ob-token-secret" });

test("outbrain list_accounts: OB-TOKEN-V1 header, marketers list (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { count: 1, marketers: [{ id: "m1", name: "my marketer", enabled: true }] } }; });
  const res = await client.callTool({ name: "list_accounts", arguments: {} });
  assert.equal(res.isError, false);
  assert.equal(seen[0].url.href, "https://api.outbrain.com/amplify/v0.1/marketers");
  assert.equal(seen[0].init.headers["OB-TOKEN-V1"], "ob-token-secret");
  assert.equal(res.structuredContent.accounts[0].id, "m1");
});

test("outbrain pause_resume: PUT /campaigns/{id} with JSON boolean enabled (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { id: "cmp9", enabled: false } }; });
  const res = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "cmp9", action: "pause" } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].init.method, "PUT");
  assert.equal(seen[0].url.href, "https://api.outbrain.com/amplify/v0.1/campaigns/cmp9");
  assert.deepEqual(JSON.parse(seen[0].init.body), { enabled: false });
});
