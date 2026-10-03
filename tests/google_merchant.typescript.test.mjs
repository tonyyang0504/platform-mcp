import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/google_merchant.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const P = "PLATFORM_MCP_GOOGLE_MERCHANT_";
Object.assign(process.env, { [P + "CLIENT_ID"]: "cid", [P + "CLIENT_SECRET"]: "GOCSPX-secret", [P + "REFRESH_TOKEN"]: "1//refresh-secret", [P + "ACCOUNT_ID"]: "123456",
  [P + "DATA_SOURCE"]: "accounts/123456/dataSources/104628", [P + "CONTENT_LANGUAGE"]: "en", [P + "FEED_LABEL"]: "US" });
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

test("google_merchant: delete builds the product input name (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => { seen.push({ url, init }); if (url.href === "https://oauth2.googleapis.com/token") return { body: { access_token: "ya29.token", expires_in: 3599 } }; return { body: {} }; });
  const res = await client.callTool({ name: "end_listing", arguments: { listing_id: "sku123" } });
  assert.equal(res.isError, false);
  const del = seen.find((s) => s.init.method === "DELETE");
  assert.equal(del.url.pathname, "/products/v1/accounts/123456/productInputs/en~US~sku123");
  assert.equal(del.url.searchParams.get("dataSource"), "accounts/123456/dataSources/104628");
  assert.equal(del.init.headers.Authorization, "Bearer ya29.token");
});
