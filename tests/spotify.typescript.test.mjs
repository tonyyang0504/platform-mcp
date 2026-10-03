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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/spotify.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_SPOTIFY_CLIENT_ID: "spcid", PLATFORM_MCP_SPOTIFY_CLIENT_SECRET: "spsecret", PLATFORM_MCP_SPOTIFY_REFRESH_TOKEN: "sprefresh1", PLATFORM_MCP_SPOTIFY_AD_ACCOUNT_ID: "acc1" });

test("spotify pause_resume: basic-auth refresh then PATCH campaign status (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.hostname === "accounts.spotify.com") return { body: { access_token: "SPTOKEN1", expires_in: 3600 } };
    return { body: { id: "c1", status: "PAUSED" } };
  });
  const res = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "c1", action: "pause" } });
  assert.equal(res.isError, false);
  assert.match(seen[0].init.headers.Authorization, /^Basic /);
  assert.equal(seen[1].url.href, "https://api-partner.spotify.com/ads/v3/ad_accounts/acc1/campaigns/c1");
  assert.deepEqual(JSON.parse(seen[1].init.body), { status: "PAUSED" });
});
