import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/coupang.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => JSON.stringify(r.body ?? {}) }; };

process.env.PLATFORM_MCP_COUPANG_ACCESS_KEY = "AK1";
process.env.PLATFORM_MCP_COUPANG_SECRET_KEY = "sec";
process.env.PLATFORM_MCP_COUPANG_VENDOR_ID = "A00012345";

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("coupang: set_inventory signs PUT path with CEA HMAC (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { code: "SUCCESS", message: "" } }; });
  const res = await client.callTool({ name: "set_inventory", arguments: { listing_id: "3572784698", quantity: 15 } });
  assert.equal(res.isError, false);
  assert.equal(seen.init.method, "PUT");
  assert.equal(seen.url.pathname, "/v2/providers/seller_api/apis/api/v1/marketplace/vendor-items/3572784698/quantities/15");
  const m = seen.init.headers.Authorization.match(/^CEA algorithm=HmacSHA256, access-key=AK1, signed-date=(\d{6}T\d{6}Z), signature=([0-9a-f]{64})$/);
  assert.ok(m);
  assert.equal(m[2], crypto.createHmac("sha256", "sec").update(`${m[1]}PUT${seen.url.pathname}`).digest("hex"));
});

test("coupang: update_listing price path + force flag (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { code: "SUCCESS" } }; });
  const res = await client.callTool({ name: "update_listing", arguments: { listing_id: "3572784698", price: 49000 } });
  assert.equal(res.isError, false);
  assert.equal(seen.pathname.endsWith("/vendor-items/3572784698/prices/49000"), true);
  assert.equal(seen.searchParams.get("forceSalePriceUpdate"), "true");
});

test("coupang: code ERROR in a 200 body is an error (wire)", async () => {
  const client = await connect(() => ({ body: { code: "ERROR", message: "not found" } }));
  const res = await client.callTool({ name: "end_listing", arguments: { listing_id: "1" } });
  assert.equal(res.isError, true);
});
