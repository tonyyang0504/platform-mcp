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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/adroll.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_ADROLL_TOKEN: "patTOKEN123", PLATFORM_MCP_ADROLL_CLIENT_ID: "APPKEY" });

test("adroll pause_resume: Token header, apikey query, unpause path (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { results: "approved" } }; });
  const res = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "CYTQ", action: "resume" } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].init.method, "PUT");
  assert.equal(seen[0].url.pathname, "/api/v1/campaign/unpause");
  assert.equal(seen[0].url.searchParams.get("campaign"), "CYTQ");
  assert.equal(seen[0].url.searchParams.get("apikey"), "APPKEY");
  assert.equal(seen[0].init.headers.Authorization, "Token patTOKEN123");
  assert.equal(res.structuredContent.status, "approved");
});
