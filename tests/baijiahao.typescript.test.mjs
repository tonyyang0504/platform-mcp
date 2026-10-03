import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/baijiahao.json", import.meta.url), "utf8"));
const CREDS = { app_id: "1111111111", app_token: "tok-secret" };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, CREDS, 50, "test", fakeFetch(handler), SPEC.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("baijiahao: read_comments posts app_id/app_token in the JSON body", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { errno: 0, errmsg: "成功", data: { items: { reply_list: [{ reply_id: "114", uname: "u", content: "hi", create_time: 1562829148 }] } } } }; });
  const res = await client.callTool({ name: "read_comments", arguments: { post_id: "111", limit: 5 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.comments[0].id, "114");
  assert.equal(seen.url.pathname, "/builderinner/open/resource/query/articleCommentList");
  assert.equal(seen.init.method, "POST");
  assert.deepEqual(JSON.parse(seen.init.body), { app_id: CREDS.app_id, app_token: CREDS.app_token, article_id: "111", page_no: 1, page_size: 5 });
});

test("baijiahao: errno != 0 is an error; analytics maps counts", async () => {
  const client = await connect((url) => url.pathname.endsWith("/article/withdraw")
    ? { body: { data: null, errno: 60001003, errmsg: "撤回或修改时文章状态错误" } }
    : { body: { errno: 0, errmsg: "成功", data: { view_count: 10, likes_count: 2, comment_count: 1 } } });
  const ok = await client.callTool({ name: "analytics_post", arguments: { post_id: "1" } });
  assert.equal(ok.structuredContent.views, 10);
  const bad = await client.callTool({ name: "delete", arguments: { post_id: "1" } });
  assert.equal(bad.isError, true);
});
