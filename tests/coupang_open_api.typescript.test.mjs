import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/coupang_open_api.json", import.meta.url), "utf8"));

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { access_key: "AK1", secret_key: "sec", vendor_id: "A00012345" }, 50, "test", fakeFetch(handler), SPEC.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("get_product signs the path with CEA HMAC (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { code: "SUCCESS", data: { sellerProductId: 309323422, sellerProductName: "해피바스 클렌징 오일", brand: "해피바스", items: [{ salePrice: 10000, externalVendorSku: "0001" }] } } }; });
  const res = await client.callTool({ name: "get_product", arguments: { id: "309323422" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.price, 10000);
  assert.equal(res.structuredContent.sku, "0001");
  const m = seen.init.headers.Authorization.match(/^CEA algorithm=HmacSHA256, access-key=AK1, signed-date=(\d{6}T\d{6}Z), signature=([0-9a-f]{64})$/);
  assert.ok(m);
  assert.equal(m[2], crypto.createHmac("sha256", "sec").update(`${m[1]}GET${seen.url.pathname}`).digest("hex"));
});
