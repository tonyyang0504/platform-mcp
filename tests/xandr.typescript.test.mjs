import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (r.raw ?? JSON.stringify(r.body ?? {})) }; };
async function connect(spec, handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(spec);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/xandr.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_XANDR_USERNAME: "api-user", PLATFORM_MCP_XANDR_PASSWORD: "PASSWORD-xd", PLATFORM_MCP_XANDR_ADVERTISER_ID: "11" });
const AUTH = { response: { status: "OK", token: "h20hbtptiv3vlp1rkm3ve1qig0" } };

test("xandr nested auth body and scheme-less Authorization token (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return url.pathname === "/auth" ? { body: AUTH } : { body: { response: { status: "OK", user: { id: 5 } } } }; });
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, false);
  assert.deepEqual(JSON.parse(seen[0].init.body), { auth: { username: "api-user", password: "PASSWORD-xd" } });
  assert.equal(seen[1].url.href, "https://api.appnexus.com/user?current");
  assert.equal(seen[1].init.headers.Authorization, "h20hbtptiv3vlp1rkm3ve1qig0");
});

test("xandr line items list and pause PUT (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); if (url.pathname === "/auth") return { body: AUTH };
    return init.method === "PUT" ? { body: { response: { status: "OK", id: 152083 } } } : { body: { response: { status: "OK", count: 1, "line-items": [{ id: 152083, name: "LI", state: "active" }] } } }; });
  const list = await client.callTool({ name: "list_campaigns", arguments: { account_id: "11" } });
  assert.equal(list.structuredContent.campaigns[0].id, "152083");
  assert.equal(seen[1].url.searchParams.get("advertiser_id"), "11");
  const res = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "152083", action: "resume" } });
  assert.equal(res.isError, false);
  const put = seen.find((s) => s.init.method === "PUT");
  assert.equal(put.url.searchParams.get("id"), "152083");
  assert.equal(put.url.searchParams.get("advertiser_id"), "11");
  assert.deepEqual(JSON.parse(put.init.body), { "line-item": { state: "active" } });
});
