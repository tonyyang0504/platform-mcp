import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/marketplaces/hotmart.json", import.meta.url), "utf8"));
process.env.PLATFORM_MCP_HOTMART_CLIENT_ID = "cid-abc";
process.env.PLATFORM_MCP_HOTMART_CLIENT_SECRET = "SECRETxyz";
process.env.PLATFORM_MCP_HOTMART_BASIC_TOKEN = "BASICtoken64";
async function connect(handler) {
  globalThis.fetch = async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null) }, text: async () => JSON.stringify(r.body ?? {}) }; };
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("hotmart: templated token URL + Basic header, cursor-paginated products (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => {
    seen.push({ url, init });
    if (url.hostname === "api-sec-vlc.hotmart.com") return { body: { access_token: "AT-1", expires_in: 172799 } };
    return { body: { items: [{ id: 698441, name: "Product A", status: "DRAFT", created_at: 1586459699000 }], page_info: { next_page_token: "NEXT" } } };
  });
  const res = await client.callTool({ name: "list_products", arguments: { status: "ACTIVE", limit: 20, cursor: "PREV" } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.equal(res.structuredContent.products[0].id, "698441");
  assert.equal(res.structuredContent.next_cursor, "NEXT");
  const tok = seen[0];
  assert.equal(tok.url.searchParams.get("client_id"), "cid-abc");
  assert.equal(tok.url.searchParams.get("client_secret"), "SECRETxyz");
  assert.equal(tok.init.headers.Authorization, "Basic BASICtoken64");
  const api = seen[1];
  assert.equal(api.url.pathname, "/products/api/v1/products");
  assert.deepEqual(Object.fromEntries(api.url.searchParams), { status: "ACTIVE", max_results: "20", page_token: "PREV" });
});
