import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/farcaster.json", import.meta.url), "utf8"));
const SIGNER = "19d0c5fd-9b33-4a48-a0e2-bc7b0555baec";
const HASH = "0x71d5225f77e0164388b1d4c120825f3a2c1f131c";
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_key: "neynar-key", signer_uuid: SIGNER, fid: "3" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("farcaster publish_text posts a cast with the signer and the x-api-key header (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { success: true, cast: { hash: HASH, author: { fid: 3 }, text: "gm" } } }; });
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["analytics_post", "delete", "me", "publish_image", "publish_text", "read_comments", "read_mentions", "reply_comment"]);
  const res = await client.callTool({ name: "publish_text", arguments: { text: "gm", reply_to: "0xparent" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.id, HASH);
  assert.equal(seen.url.href, "https://api.neynar.com/v2/farcaster/cast/");
  assert.deepEqual(JSON.parse(seen.init.body), { signer_uuid: SIGNER, text: "gm", parent: "0xparent" });
  assert.equal(seen.init.headers["x-api-key"], "neynar-key");
  assert.equal(seen.init.headers.Authorization, undefined);
  const img = await client.callTool({ name: "publish_image", arguments: { text: "pics", image_urls: ["https://img.example/a.png", "https://img.example/b.png", "https://img.example/c.png"] } });
  assert.equal(img.isError, false);
  assert.deepEqual(JSON.parse(seen.init.body), { signer_uuid: SIGNER, text: "pics", embeds: [{ url: "https://img.example/a.png" }, { url: "https://img.example/b.png" }] });
});

test("farcaster read_comments reads direct_replies and delete sends a DELETE with a JSON body (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => {
    seen.push({ url, init });
    if (init.method === "DELETE") return { body: { success: true, message: "Cast deleted" } };
    return { body: { conversation: { cast: { hash: HASH, direct_replies: [{ hash: "0xreply1", author: { fid: 5, username: "zsc" }, text: "nice", timestamp: "2026-09-24T10:05:00.000Z" }] } }, next: { cursor: null } } };
  });
  const res = await client.callTool({ name: "read_comments", arguments: { post_id: HASH } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].url.pathname, "/v2/farcaster/cast/conversation/");
  assert.equal(seen[0].url.searchParams.get("identifier"), HASH);
  assert.equal(seen[0].url.searchParams.get("type"), "hash");
  assert.equal(seen[0].url.searchParams.get("reply_depth"), "1");
  assert.equal(seen[0].url.searchParams.get("limit"), "20");
  assert.equal(res.structuredContent.comments[0].author, "zsc");
  const del = await client.callTool({ name: "delete", arguments: { post_id: HASH } });
  assert.equal(del.isError, false);
  assert.equal(del.structuredContent.status, "deleted");
  assert.equal(seen[1].url.href, "https://api.neynar.com/v2/farcaster/cast/");
  assert.equal(seen[1].init.method, "DELETE");
  assert.deepEqual(JSON.parse(seen[1].init.body), { signer_uuid: SIGNER, target_hash: HASH });
});
