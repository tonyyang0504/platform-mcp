import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => ({ "content-type": "application/json" })[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(file, creds, handler) {
  const spec = JSON.parse(readFileSync(new URL(`../catalog/${file}`, import.meta.url), "utf8"));
  const a = spec.adapter;
  const server = buildServer(spec, new Transport(a.base_url, a.auth, { ...creds }, 50, "test", fakeFetch(handler), a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

function check(url, secret) {
  const q = Object.fromEntries(url.searchParams); const sig = q.sign; delete q.sign;
  assert.equal(sig, crypto.createHash("md5").update(secret + Object.keys(q).sort().map((k) => k + q[k]).join("") + secret).digest("hex").toUpperCase());
  return q;
}

test("taobao_fenxiao_alimama: 淘宝联盟 material search is signed without a session", async () => {
  const creds = { app_key: "23456789", app_secret: "tbk-secret-0987", adzone_id: "12345678" };
  let seen;
  const client = await connect("ecommerce_suppliers/taobao_fenxiao_alimama.json", creds, (url) => { seen = url; return { body: { tbk_dg_material_optional_upgrade_response: { total_results: 1, result_list: { map_data: [{ item_id: "abc-1", item_basic_info: { title: "连衣裙" }, price_promotion_info: { zk_final_price: "88.00" } }] } } } }; });
  const res = await client.callTool({ name: "list_products", arguments: { query: "女装" } });
  assert.equal(res.structuredContent.products[0].id, "abc-1"); assert.equal(res.structuredContent.products[0].price, "88.00");
  const q = check(seen, creds.app_secret);
  assert.equal(q.adzone_id, "12345678"); assert.equal(q.q, "女装"); assert.equal(q.session, undefined);
});
