import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => ({ "content-type": "application/json" })[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/kuaishou.json", import.meta.url), "utf8"));
const CREDS = { app_id: "ks123456", app_secret: "KS-SECRET-9876", refresh_token: "RT-ks-1" };

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

test("kuaishou: GET refresh with app_id/app_secret, rotation, query token (wire)", async () => {
  const log = [];
  const { client, t } = await connect((url, init) => { log.push({ url, init });
    if (url.pathname === "/oauth2/refresh_token") return { body: { result: 1, access_token: "AT-ks-1", expires_in: 172800, refresh_token: "RT-ks-2" } };
    return { body: { result: 1, video_info: { photo_id: "3xw", like_count: 4, view_count: 99 } } }; });
  const res = await client.callTool({ name: "analytics_post", arguments: { post_id: "3xw" } });
  assert.equal(res.isError, false); assert.equal(res.structuredContent.metrics.view_count, 99);
  assert.equal(log[0].init.method ?? "GET", "GET");
  assert.deepEqual(Object.fromEntries(log[0].url.searchParams), { grant_type: "refresh_token", refresh_token: "RT-ks-1", app_id: "ks123456", app_secret: "KS-SECRET-9876" });
  assert.equal(t.creds.refresh_token, "RT-ks-2");
  assert.equal(log[1].url.searchParams.get("access_token"), "AT-ks-1"); assert.equal(log[1].url.searchParams.get("app_id"), "ks123456"); assert.equal(log[1].url.searchParams.get("photo_id"), "3xw");
});

test("kuaishou: delete and a non-1 result", async () => {
  const { client } = await connect((url) => url.pathname === "/oauth2/refresh_token" ? { body: { result: 1, access_token: "AT", expires_in: 172800 } }
    : url.pathname.endsWith("/delete") ? { body: { result: 1 } } : { body: { result: 120001, error_msg: "视频不存在" } });
  assert.equal((await client.callTool({ name: "delete", arguments: { post_id: "p1" } })).structuredContent.status, "deleted");
  assert.equal((await client.callTool({ name: "me", arguments: {} })).isError, true);
});
