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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/otto_retail_media.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_OTTO_RETAIL_MEDIA_CLIENT_ID: "ottocid", PLATFORM_MCP_OTTO_RETAIL_MEDIA_CLIENT_SECRET: "ottosecret" });

test("otto_retail_media pause_resume: merge-patch status, pending change request (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.pathname === "/v1/token") return { body: { access_token: "OTTOJWT", expires_in: 1800 } };
    return { status: 202, body: { changeRequest: { requestId: "3fa8", status: "PENDING" } } };
  });
  const res = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "a1b2", action: "pause" } });
  assert.equal(res.isError, false);
  assert.equal(form(seen[0].init.body).scope, "advertising-services");
  assert.equal(seen[1].init.method, "PATCH");
  assert.equal(seen[1].init.headers["Content-Type"], "application/merge-patch+json");
  assert.deepEqual(JSON.parse(seen[1].init.body), { status: "PAUSED" });
  assert.equal(res.structuredContent.status, "PENDING");
});
