import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/lazada_open_platform.json", import.meta.url), "utf8"));
const CREDS = { app_key: "100132", app_secret: "laz-secret-0123456789", access_token: "50000601237osiQodfgbhs2iXplQ1f0dDfs9Wj0frtc3d1E2d0Nm", domain: "co.th" };

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", fakeFetch(handler), a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

function checkSign(url, apiName) {
  const params = Object.fromEntries(url.searchParams); const sig = params.sign; delete params.sign;
  const base = apiName + Object.keys(params).sort().map((k) => k + params[k]).join("");
  assert.equal(sig, crypto.createHmac("sha256", CREDS.app_secret).update(base).digest("hex").toUpperCase());
  return params;
}

test("lazada_open_platform: product item is signed over /product/item/get (no /rest)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { code: "0", data: { item_id: "180226526", attributes: { name: "asd" }, skus: [{ SellerSku: "39817:01:01", price: 32, quantity: 5 }] } } }; });
  const res = await client.callTool({ name: "get_product", arguments: { id: "180226526" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.sku, "39817:01:01");
  assert.equal(seen.host, "api.lazada.co.th");
  assert.equal(seen.pathname, "/rest/product/item/get");
  const p = checkSign(seen, "/product/item/get");
  assert.equal(p.item_id, "180226526");
  assert.equal(p.sign_method, "sha256");
});

test("lazada_open_platform: non-zero code is an error result", async () => {
  const client = await connect(() => ({ body: { code: "16", message: "E016: Invalid Order ID" } }));
  const res = await client.callTool({ name: "get_order", arguments: { id: "1" } });
  assert.equal(res.isError, true);
});
