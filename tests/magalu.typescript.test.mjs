import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/magalu.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => JSON.stringify(r.body ?? {}) }; };
Object.assign(process.env, { PLATFORM_MCP_MAGALU_CLIENT_ID: "mg-client", PLATFORM_MCP_MAGALU_CLIENT_SECRET: "MGSECRETvalue", PLATFORM_MCP_MAGALU_REFRESH_TOKEN: "RT-magalu-1", PLATFORM_MCP_MAGALU_CHANNEL_ID: "ch-1" });
delete process.env.PLATFORM_MCP_STATE_DIR;

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("magalu: stock PATCH after refresh (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => { seen.push({ url, init }); if (url.host === "id.magalu.com") return { body: { access_token: "eyJ.acc", expires_in: 7200 } }; return { status: 202, body: { trace_id: "tr" } }; });
  const res = await client.callTool({ name: "set_inventory", arguments: { sku: "SKU-1", quantity: 7 } });
  assert.equal(res.isError, false);
  const p = seen.find((s) => s.url.pathname === "/seller/v1/portfolios/stocks/SKU-1");
  assert.equal(p.init.method, "PATCH");
  assert.equal(p.init.headers.Authorization, "Bearer eyJ.acc");
  assert.deepEqual(JSON.parse(p.init.body), { channel: { id: "ch-1" }, type: "AVAILABLE", quantity: 7 });
});
