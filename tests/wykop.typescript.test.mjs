import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/wykop.json", import.meta.url), "utf8"));
process.env.PLATFORM_MCP_WYKOP_APP_KEY = "devkopapp";
process.env.PLATFORM_MCP_WYKOP_APP_SECRET = "SECRETdevkop";
async function connect(handler) {
  globalThis.fetch = async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null) }, text: async () => JSON.stringify(r.body ?? {}) }; };
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("wykop: nested app login then entry comments (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => {
    seen.push({ url, init });
    if (url.pathname === "/api/v3/auth") return { body: { data: { token: "APPJWT" } } };
    return { body: { data: [{ id: 11, author: { username: "devkopuser" }, created_at: "2019-02-25 20:35", content: "hej" }], pagination: { per_page: 25, total: 1 } } };
  });
  const res = await client.callTool({ name: "read_comments", arguments: { post_id: "2341" } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.equal(res.structuredContent.comments[0].author, "devkopuser");
  assert.deepEqual(JSON.parse(seen[0].init.body), { data: { key: "devkopapp", secret: "SECRETdevkop" } });
  assert.equal(seen[1].url.pathname, "/api/v3/entries/2341/comments");
  assert.equal(seen[1].init.headers.Authorization, "Bearer APPJWT");
});
