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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/partnerize.json", import.meta.url), "utf8"));
Object.assign(process.env, { PLATFORM_MCP_PARTNERIZE_APPLICATION_KEY: "pz-app", PLATFORM_MCP_PARTNERIZE_USER_API_KEY: "pz-user-secret" });

test("partnerize list_accounts: basic auth, v3 brand list (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { data: [{ brand_id: "111111l1", brand_name: "Brand One" }] } }; });
  const res = await client.callTool({ name: "list_accounts", arguments: {} });
  assert.equal(res.isError, false);
  assert.equal(seen[0].url.href, "https://api.partnerize.com/v3/brand");
  assert.equal(seen[0].init.headers.Authorization, "Basic " + Buffer.from("pz-app:pz-user-secret").toString("base64"));
  assert.deepEqual([res.structuredContent.accounts[0].id, res.structuredContent.accounts[0].name], ["111111l1", "Brand One"]);
});
