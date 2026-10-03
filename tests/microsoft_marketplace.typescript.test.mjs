import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/marketplaces/microsoft_marketplace.json", import.meta.url), "utf8"));
process.env.PLATFORM_MCP_MICROSOFT_MARKETPLACE_CLIENT_ID = "app-1";
process.env.PLATFORM_MCP_MICROSOFT_MARKETPLACE_CLIENT_SECRET = "SECRETentra";
process.env.PLATFORM_MCP_MICROSOFT_MARKETPLACE_TENANT_ID = "tenant-123";
async function connect(handler) {
  globalThis.fetch = async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null) }, text: async () => JSON.stringify(r.body ?? {}) }; };
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("microsoft_marketplace: tenant token URL and product query (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => {
    seen.push({ url, init });
    if (url.hostname === "login.microsoftonline.com") return { body: { access_token: "GRAPH-AT", expires_in: 3599 } };
    return { body: { value: [{ id: "product/1234-abcd", alias: "Contoso", type: "softwareAsAService" }] } };
  });
  const res = await client.callTool({ name: "list_products", arguments: { limit: 5 } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.equal(res.structuredContent.products[0].name, "Contoso");
  assert.equal(seen[0].url.pathname, "/tenant-123/oauth2/v2.0/token");
  assert.match(String(seen[0].init.body), /scope=https%3A%2F%2Fgraph\.microsoft\.com%2F\.default/);
  assert.equal(seen[1].url.pathname, "/rp/product-ingestion/product");
  assert.equal(seen[1].url.searchParams.get("$version"), "2022-03-01-preview3");
  assert.equal(seen[1].url.searchParams.get("$maxpagesize"), "5");
});
