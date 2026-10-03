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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/revcontent.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_REVCONTENT_CLIENT_ID: "rccid", PLATFORM_MCP_REVCONTENT_CLIENT_SECRET: "rcsecret40chars" });

test("revcontent update_budget: daily budget settings POST (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => {
    seen.push({ url, init });
    if (url.pathname === "/oauth/token") return { body: { access_token: "20b9c0a27315af", expires_in: 86400 } };
    return { body: { id: "218", budget: "80.00", success: true } };
  });
  const res = await client.callTool({ name: "update_budget", arguments: { campaign_id: "218", daily_budget: 80 } });
  assert.equal(res.isError, false);
  assert.equal(seen[1].url.pathname, "/stats/api/v1.0/boosts/218/settings");
  assert.deepEqual(JSON.parse(seen[1].init.body), { budget_type: "daily", budget_amount: 80 });
  assert.equal(res.structuredContent.status, "updated");
});
