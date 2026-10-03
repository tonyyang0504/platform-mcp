import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => ({ "content-type": "application/json" })[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/tiktok.json", import.meta.url), "utf8"));
const CREDS = { client_key: "awCLIENTKEY01", client_secret: "TT-SECRET-0123", refresh_token: "rft.one-abc", privacy_level: "SELF_ONLY" };

async function connect(handler) {
  const a = SPEC.adapter;
  const t = new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", fakeFetch(handler), a.envelope ?? {});
  const server = buildServer(SPEC, t);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return { client, t };
}

test("tiktok (social): client_key refresh grant, rotation and photo post (wire)", async () => {
  const log = [];
  const { client, t } = await connect((url, init) => { log.push({ url, init });
    if (url.pathname === "/v2/oauth/token/") return { body: { access_token: "act.minted-1", expires_in: 86400, refresh_token: "rft.two-def" } };
    return { body: { data: { publish_id: "p_pub_url~v2.9" }, error: { code: "ok" } } }; });
  const res = await client.callTool({ name: "publish_image", arguments: { text: "hi", image_urls: ["https://cdn.example.com/a.webp"] } });
  assert.equal(res.isError, false); assert.equal(res.structuredContent.id, "p_pub_url~v2.9");
  const form = Object.fromEntries(new URLSearchParams(String(log[0].init.body)));
  assert.deepEqual(form, { client_key: "awCLIENTKEY01", client_secret: "TT-SECRET-0123", grant_type: "refresh_token", refresh_token: "rft.one-abc" });
  assert.equal(t.creds.refresh_token, "rft.two-def");
  assert.equal(log[1].init.headers.Authorization, "Bearer act.minted-1");
  const body = JSON.parse(log[1].init.body);
  assert.equal(body.post_info.privacy_level, "SELF_ONLY"); assert.deepEqual(body.source_info.photo_images, ["https://cdn.example.com/a.webp"]); assert.equal(body.source_info.photo_cover_index, 0);
});

test("tiktok (social): analytics_post reads the counts of one video", async () => {
  const { client } = await connect((url) => url.pathname === "/v2/oauth/token/" ? { body: { access_token: "act.x", expires_in: 86400 } }
    : { body: { data: { videos: [{ id: "707", like_count: 3, view_count: 90 }] }, error: { code: "ok" } } });
  const res = await client.callTool({ name: "analytics_post", arguments: { post_id: "707" } });
  assert.equal(res.structuredContent.post_id, "707"); assert.equal(res.structuredContent.metrics.view_count, 90);
});
