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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/stackadapt.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_STACKADAPT_REST_API_KEY: "sa-rest-secret" });

test("stackadapt list_campaigns: X-Authorization, page query (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { total_campaigns: 1, data: [{ id: 55, name: "API Test Campaign", state: "active", budget: 10000 }] } }; });
  const res = await client.callTool({ name: "list_campaigns", arguments: { account_id: "12", page: 3 } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].url.href, "https://api.stackadapt.com/service/v2/campaigns?page=3");
  assert.equal(seen[0].init.headers["X-Authorization"], "sa-rest-secret");
  assert.equal(res.structuredContent.campaigns[0].status, "active");
});
