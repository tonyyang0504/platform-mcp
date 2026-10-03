import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/jd_worldwide_open.json", import.meta.url), "utf8"));
const CREDS = { app_key: "123456780233FA31AD94AA59CFA65305", app_secret: "jd-secret-0123456789", access_token: "12345678-b0e1-4d0c-9d10-a998d9597d75" };

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", fakeFetch(handler), a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

function checkSign(url) {
  const params = Object.fromEntries(url.searchParams); const sig = params.sign; delete params.sign;
  const base = Object.keys(params).sort().map((k) => k + params[k]).join("");
  assert.equal(sig, crypto.createHash("md5").update(CREDS.app_secret + base + CREDS.app_secret).digest("hex").toUpperCase());
  assert.match(params.timestamp, /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/);
  const beijing = new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(0, 16).replace("T", " ");
  assert.equal(params.timestamp.slice(0, 16), beijing);
  return params;
}

test("jd_worldwide_open: findWareById is signed with a Beijing-time timestamp", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { jingdong_ware_read_findWareById_responce: { ware: { wareId: "1", title: "iphone15手机", jdPrice: "1", stockNum: "1", itemNum: "111" } } } }; });
  const res = await client.callTool({ name: "get_product", arguments: { id: "1" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.title, "iphone15手机");
  const p = checkSign(seen);
  assert.equal(p.method, "jingdong.ware.read.findWareById");
  assert.equal(JSON.parse(p["360buy_param_json"]).wareId, 1);
});

test("jd_worldwide_open: error_response is an error result", async () => {
  const client = await connect(() => ({ body: { error_response: { code: "19", zh_desc: "token已过期", en_desc: "Invalid access_token" } } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
});
