import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => ({ "content-type": "application/json" })[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/zalo.json", import.meta.url), "utf8"));
const CREDS = { app_id: "4318123456", secret_key: "ZALO-SECRET-abc", refresh_token: "RT-zalo-1", author: "Shop News", cover_photo_url: "https://cdn.example.com/cover.jpg" };

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", fakeFetch(handler), a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("zalo (social): publish_text creates an OA article (wire)", async () => {
  const log = [];
  const client = await connect((url, init) => { log.push({ url, init });
    if (url.host === "oauth.zaloapp.com") return { body: { access_token: "AT-zalo-1", refresh_token: "RT-zalo-2", expires_in: "90000" } };
    return { body: { error: 0, message: "Success", data: { token: "9xk0" } } }; });
  const res = await client.callTool({ name: "publish_text", arguments: { text: "Khai trương" } });
  assert.equal(res.isError, false); assert.equal(res.structuredContent.id, "9xk0");
  const body = JSON.parse(log[1].init.body);
  assert.equal(body.title, "Khai trương"); assert.equal(body.author, "Shop News"); assert.equal(body.cover.photo_url, CREDS.cover_photo_url);
  assert.deepEqual(body.body, [{ type: "text", content: "Khai trương" }]);
  assert.equal(log[1].init.headers.access_token, "AT-zalo-1");
});

test("zalo (social): delete an article", async () => {
  const log = [];
  const client = await connect((url, init) => { log.push({ url, init }); return url.host === "oauth.zaloapp.com" ? { body: { access_token: "AT" } } : { body: { error: 0, message: "Success" } }; });
  const res = await client.callTool({ name: "delete", arguments: { post_id: "39c0" } });
  assert.equal(res.structuredContent.status, "deleted");
  assert.deepEqual(JSON.parse(log[1].init.body), { id: "39c0" });
});
