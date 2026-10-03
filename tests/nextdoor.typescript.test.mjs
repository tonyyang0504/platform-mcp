import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

// ads/nextdoor (Nextdoor Ads API v3); the social Publish API is tested in nextdoor_social.typescript.test.mjs
const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/nextdoor.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { api_token: "nam-secret-token", advertiser_id: "adv1" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("nextdoor ads: pause_resume puts user_status on the configured advertiser (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { id: "c1", status: "ACTIVE", user_status: "ACTIVE" } }; });
  const res = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "c1", action: "resume" } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.href, "https://ads.nextdoor.com/api/v3/advertisers/adv1/campaigns/c1/status");
  assert.equal(seen.init.method, "PUT");
  assert.deepEqual(JSON.parse(seen.init.body), { user_status: "ACTIVE" });
  assert.equal(seen.init.headers.Authorization, "Bearer nam-secret-token");
});
