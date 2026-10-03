import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/marketplaces/poe.json", import.meta.url), "utf8"));
process.env.PLATFORM_MCP_POE_API_KEY = "sk_test_POEKEY123";
async function connect(handler) {
  globalThis.fetch = async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null) }, text: async () => JSON.stringify(r.body ?? {}) }; };
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("poe: bots listed as products with the per-token prompt price (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { bots: [{ handle: "MyCustomBot", description: "d", api_bot_settings: { pricing: { prompt: "0.00003" } } }] } }; });
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["list_products", "me"]);
  const res = await client.callTool({ name: "list_products", arguments: {} });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.equal(res.structuredContent.products[0].raw.api_bot_settings.pricing.prompt, "0.00003");
  assert.equal(seen.url.href, "https://api.poe.com/bots");
  assert.equal(seen.init.headers.Authorization, "Bearer sk_test_POEKEY123");
});
