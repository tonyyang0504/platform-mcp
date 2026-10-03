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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/snapchat.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_SNAPCHAT_CLIENT_ID: "snapcid", PLATFORM_MCP_SNAPCHAT_CLIENT_SECRET: "snapsecret", PLATFORM_MCP_SNAPCHAT_REFRESH_TOKEN: "snaprefresh1", PLATFORM_MCP_SNAPCHAT_AD_ACCOUNT_ID: "acc1" });

test("snapchat pause_resume: JSON Patch array body (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.hostname === "accounts.snapchat.com") return { body: { access_token: "0.SNAPTOKEN", expires_in: 3600 } };
    return { body: { request_status: "SUCCESS", campaigns: [{ campaign: { id: "c1", status: "ACTIVE" } }] } };
  });
  const res = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "c1", action: "resume" } });
  assert.equal(res.isError, false);
  assert.equal(seen[1].init.method, "PATCH");
  assert.equal(seen[1].url.href, "https://adsapi.snapchat.com/v1/adaccounts/acc1/campaigns/c1");
  assert.equal(seen[1].init.headers["Content-Type"], "application/json-patch+json");
  assert.deepEqual(JSON.parse(seen[1].init.body), [{ op: "replace", path: "/status", value: "ACTIVE" }]);
  assert.equal(res.structuredContent.status, "ACTIVE");
});
