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
const names = async (spec) => (await (await connect(spec, () => ({}))).listTools()).tools.map((t) => t.name).sort();
const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/trustpilot.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_TRUSTPILOT_CLIENT_ID: "key", PLATFORM_MCP_TRUSTPILOT_CLIENT_SECRET: "sec", PLATFORM_MCP_TRUSTPILOT_REFRESH_TOKEN: "RT", PLATFORM_MCP_TRUSTPILOT_BUSINESS_UNIT_ID: "507f", PLATFORM_MCP_TRUSTPILOT_BUSINESS_USER_ID: "u9" });
const TOKEN = "https://api.trustpilot.com/v1/oauth/oauth-business-users-for-applications/refresh";
const tok = { body: { access_token: "AT", expires_in: 359999 } };

test("trustpilot: tools (wire)", async () => {
  assert.deepEqual(await names(SPEC), ["me", "read_mentions", "reply_comment"]);
});

test("trustpilot: private reviews as mentions (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return url.href === TOKEN ? tok : { body: { reviews: [{ id: "r1", text: "Great", consumer: { displayName: "John" } }] } }; });
  const res = await client.callTool({ name: "read_mentions", arguments: { limit: 10 } });
  assert.equal(res.structuredContent.mentions[0].author, "John");
  assert.match(seen[0].init.headers.Authorization, /^Basic /);
  assert.equal(seen[1].url.pathname, "/v1/private/business-units/507f/reviews");
  assert.equal(seen[1].url.searchParams.get("perPage"), "10");
});

test("trustpilot: reply to a review (wire)", async () => {
  let last;
  const client = await connect(SPEC, (url, init) => { if (url.href === TOKEN) return tok; last = { url, init }; return { status: 201, raw: "" }; });
  const res = await client.callTool({ name: "reply_comment", arguments: { comment_id: "r1", text: "Thank you" } });
  assert.equal(res.structuredContent.id, "reply");
  assert.deepEqual(JSON.parse(last.init.body), { authorBusinessUserId: "u9", message: "Thank you" });
});
