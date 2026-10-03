import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/zalando.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => (r.status === 204 ? "" : JSON.stringify(r.body ?? {})) }; };
Object.assign(process.env, { PLATFORM_MCP_ZALANDO_CLIENT_ID: "zd-client", PLATFORM_MCP_ZALANDO_CLIENT_SECRET: "ZDSECRETvalue", PLATFORM_MCP_ZALANDO_MERCHANT_ID: "m-1", PLATFORM_MCP_ZALANDO_SALES_CHANNEL_ID: "sc-1", PLATFORM_MCP_ZALANDO_CURRENCY: "EUR" });

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("zalando: tracking PATCH with JSON:API content type (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => { seen.push({ url, init }); if (url.pathname === "/auth/token") return { body: { access_token: "zd.jwt", expires_in: 7200 } }; return { status: 204 }; });
  const res = await client.callTool({ name: "mark_shipped", arguments: { order_id: "o-1", tracking_number: "0034" } });
  assert.equal(res.isError, false);
  const p = seen.find((s) => s.init.method === "PATCH");
  assert.equal(p.url.pathname, "/merchants/m-1/orders/o-1");
  assert.equal(p.init.headers["Content-Type"], "application/vnd.api+json");
  assert.equal(p.init.headers.Authorization, "Bearer zd.jwt");
  assert.deepEqual(JSON.parse(p.init.body), { data: { type: "Order", id: "o-1", attributes: { tracking_number: "0034" } } });
});
