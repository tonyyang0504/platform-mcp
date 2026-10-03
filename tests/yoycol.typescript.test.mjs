import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/yoycol.json", import.meta.url), "utf8"));

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { access_key: "AK-yoy-1", secret_key: "yoy-secret-0123456789" }, 50, "test", fakeFetch(handler), a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("yoycol: V4 HMAC signature over method, path, timestamp, nonce and sorted raw query (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { code: "100000", msg: "success", data: { records: [{ id: 101, name: "Unisex T-Shirt", spuCode: "TS-001" }] } } }; });
  const res = await client.callTool({ name: "list_products", arguments: { query: "shirt tee", page: 2, limit: 5 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.products[0].id, "101");
  const h = seen.init.headers;
  const params = Object.fromEntries(seen.url.searchParams);
  const data = `method=GET\npath=${seen.url.pathname}\ntimestamp=${h["X-API-Timestamp"]}\nnonce=${h["X-API-Nonce"]}\naccessKey=AK-yoy-1\nalgorithm=HmacSHA256\nversion=4.0\nparams=` +
    Object.keys(params).sort().map((k) => `${k}=${params[k]}`).join("&");
  assert.equal(params.query, "shirt tee");
  assert.equal(h["X-API-Signature"], crypto.createHmac("sha256", "yoy-secret-0123456789").update(data).digest("base64"));
  assert.equal(h["X-API-Nonce"].length, 32);
});

test("yoycol: non-100000 business code is an error", async () => {
  const client = await connect(() => ({ body: { code: "320001", msg: "product not found" } }));
  const res = await client.callTool({ name: "get_product", arguments: { id: "5" } });
  assert.equal(res.isError, true);
});
