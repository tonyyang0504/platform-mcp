import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/otto.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => JSON.stringify(r.body ?? {}) }; };
Object.assign(process.env, { PLATFORM_MCP_OTTO_CLIENT_ID: "otto-app", PLATFORM_MCP_OTTO_CLIENT_SECRET: "OTTOSECRETvalue", PLATFORM_MCP_OTTO_CURRENCY: "EUR" });

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("otto: token with scopes, quantity array body (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => { seen.push({ url, init }); if (url.pathname === "/v1/token") return { body: { access_token: "otto.jwt", expires_in: 1800 } }; return { status: 207, body: { results: [], errors: [] } }; });
  const res = await client.callTool({ name: "set_inventory", arguments: { sku: "SKU-1", quantity: 3 } });
  assert.equal(res.isError, false);
  assert.equal(new URLSearchParams(seen[0].init.body).get("scope"), "products availability orders shipments");
  const q = seen.find((s) => s.url.pathname === "/v1/availability/quantities");
  assert.equal(q.init.headers.Authorization, "Bearer otto.jwt");
  assert.deepEqual(JSON.parse(q.init.body), [{ sku: "SKU-1", quantity: 3 }]);
});
