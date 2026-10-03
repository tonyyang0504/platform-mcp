import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => ({ "content-type": "application/json" })[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/bilibili.json", import.meta.url), "utf8"));
const CREDS = { client_id: "93a0f774fae84e6c", client_secret: "BILI-SECRET-0123", refresh_token: "WxFDKwqScZIQ-1" };

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

const hget = (h, k) => h[k] ?? h[Object.keys(h).find((x) => x.toLowerCase() === k.toLowerCase())];

test("bilibili: query-string refresh, rotation, v2.0 signature over x-bili headers with body MD5 (wire)", async () => {
  const log = [];
  const { client, t } = await connect((url, init) => { log.push({ url, init });
    if (url.host === "api.bilibili.com") return { body: { code: 0, data: { access_token: "d30bedaa4d8e", refresh_token: "WxFDKwqScZIQ-2", expires_in: 1830220614 } } };
    return { body: { code: 0, message: "0" } }; });
  const res = await client.callTool({ name: "delete", arguments: { post_id: "BV1MW421X7gM" } });
  assert.equal(res.isError, false);
  assert.equal(log[0].url.searchParams.get("refresh_token"), "WxFDKwqScZIQ-1"); assert.equal(log[0].url.searchParams.get("client_id"), CREDS.client_id);
  assert.equal(t.creds.refresh_token, "WxFDKwqScZIQ-2");
  const h = log[1].init.headers; const body = log[1].init.body;
  assert.deepEqual(JSON.parse(body), { resource_id: "BV1MW421X7gM" });
  assert.equal(hget(h, "x-bili-content-md5"), crypto.createHash("md5").update(body).digest("hex"));
  const payload = ["x-bili-accesskeyid", "x-bili-content-md5", "x-bili-signature-method", "x-bili-signature-nonce", "x-bili-signature-version", "x-bili-timestamp"].map((k) => `${k}:${hget(h, k)}`).join("\n");
  assert.equal(hget(h, "Authorization"), crypto.createHmac("sha256", CREDS.client_secret).update(payload).digest("hex"));
  assert.equal(hget(h, "access-token"), "d30bedaa4d8e");
});

test("bilibili: analytics_post and a non-zero code", async () => {
  let n = 0;
  const { client } = await connect((url) => url.host === "api.bilibili.com" ? { body: { code: 0, data: { access_token: "A" } } }
    : (++n === 1 ? { body: { code: 0, data: { view: 29, like: 3 } } } : { body: { code: 127001, message: "access_token验证错误" } }));
  assert.equal((await client.callTool({ name: "analytics_post", arguments: { post_id: "BV1" } })).structuredContent.metrics.view, 29);
  assert.equal((await client.callTool({ name: "me", arguments: {} })).isError, true);
});
