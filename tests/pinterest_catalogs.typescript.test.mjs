import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/pinterest_catalogs.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const P = "PLATFORM_MCP_PINTEREST_CATALOGS_";
Object.assign(process.env, { [P + "CLIENT_ID"]: "1484", [P + "CLIENT_SECRET"]: "PINSECRETvalue", [P + "REFRESH_TOKEN"]: "pinr.refresh1", [P + "COUNTRY"]: "US", [P + "LANGUAGE"]: "en-US", [P + "CURRENCY"]: "USD" });
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

test("pinterest_catalogs: delete item batch (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => { seen.push({ url, init }); if (url.pathname === "/v5/oauth/token") return { body: { access_token: "pina.access", expires_in: 2592000 } }; return { body: { batch_id: "b1", status: "PROCESSING" } }; });
  const res = await client.callTool({ name: "end_listing", arguments: { listing_id: "DS0294-M" } });
  assert.equal(res.isError, false);
  const b = seen.find((s) => s.url.pathname === "/v5/catalogs/items/batch");
  assert.equal(b.init.headers.Authorization, "Bearer pina.access");
  assert.deepEqual(JSON.parse(b.init.body), { catalog_type: "RETAIL", country: "US", language: "en-US", items: [{ item_id: "DS0294-M", operation: "DELETE" }] });
});
