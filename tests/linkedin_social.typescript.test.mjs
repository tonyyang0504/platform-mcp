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
const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/linkedin.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_LINKEDIN_CLIENT_ID: "86li", PLATFORM_MCP_LINKEDIN_CLIENT_SECRET: "lisecret", PLATFORM_MCP_LINKEDIN_REFRESH_TOKEN: "AQRrt", PLATFORM_MCP_LINKEDIN_AUTHOR_URN: "urn:li:organization:5515715" });
const TOKEN = "https://www.linkedin.com/oauth/v2/accessToken";
const tok = { body: { access_token: "AQVat", expires_in: 5184000 } };

test("linkedin (social): tools (wire)", async () => {
  assert.deepEqual(await names(SPEC), ["analytics_post", "delete", "me", "read_comments", "read_mentions", "reply_comment"]);
});

test("linkedin (social): read_comments with version headers, nested reply (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { if (url.href === TOKEN) return tok; seen.push({ url, init }); return init.method === "POST" ? { status: 201, body: { commentUrn: "urn:li:comment:(urn:li:activity:9,7)" } } : { body: { elements: [{ commentUrn: "urn:li:comment:(urn:li:activity:9,8)", actor: "urn:li:person:A", message: { text: "nice" } }] } }; });
  const r = await client.callTool({ name: "read_comments", arguments: { post_id: "urn:li:share:1" } });
  assert.equal(r.structuredContent.comments[0].text, "nice");
  assert.equal(seen[0].init.headers["Linkedin-Version"], "202609");
  assert.equal(seen[0].init.headers.Authorization, "Bearer AQVat");
  const rep = await client.callTool({ name: "reply_comment", arguments: { comment_id: "urn:li:comment:(urn:li:activity:9,8)", text: "thanks" } });
  assert.equal(rep.structuredContent.id, "urn:li:comment:(urn:li:activity:9,7)");
  assert.deepEqual(JSON.parse(seen[1].init.body), { actor: "urn:li:organization:5515715", message: { text: "thanks" }, parentComment: "urn:li:comment:(urn:li:activity:9,8)" });
});

test("linkedin (social): mentions finder keeps List(...) literal, delete sends X-RestLi-Method (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { if (url.href === TOKEN) return tok; seen.push({ url, init }); return init.method === "DELETE" ? { status: 204, raw: "" } : { body: { elements: [{ notificationId: 4406044 }] } }; });
  const r = await client.callTool({ name: "read_mentions", arguments: {} });
  assert.equal(r.structuredContent.mentions[0].id, "4406044");
  assert.match(seen[0].url.href, /q=criteria&actions=List\(SHARE_MENTION\)/);
  assert.equal(seen[0].url.searchParams.get("organizationalEntity"), "urn:li:organization:5515715");
  const d = await client.callTool({ name: "delete", arguments: { post_id: "urn%3Ali%3Ashare%3A1" } });
  assert.equal(d.structuredContent.status, "deleted");
  assert.equal(seen[1].init.headers["X-RestLi-Method"], "DELETE");
});
