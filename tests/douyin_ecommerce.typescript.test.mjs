import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/douyin_ecommerce.json", import.meta.url), "utf8"));
const CREDS = { app_key: "6844048284663924231", app_secret: "749698a6-fcb3-4358-b241-ec1d93cf9c1f", access_token: "c6f957da-1239-4343-84a1-c84e68915ff7" };
const jsonResp = (status, body) => ({ status, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null) }, text: async () => JSON.stringify(body) });

test("douyin_ecommerce: hmac-sha256 sign over sorted params without access_token/sign_method, GMT+8 timestamp (wire)", async () => {
  const realNow = Date.now; Date.now = () => 1790301600000;
  try {
    const log = [];
    const f = async (url, init) => { log.push({ url, init }); return jsonResp(200, { code: 10000, msg: "success", data: { shop_order_detail: { order_id: "6496679971677798670", order_status_desc: "已发货", pay_amount: 5990, logistics_info: [{ tracking_no: "SF1", company_name: "顺丰速运" }] } } }); };
    const a = SPEC.adapter;
    const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", f, a.envelope ?? {}));
    const [ct, st] = InMemoryTransport.createLinkedPair();
    await server.connect(st);
    const c = new Client({ name: "test", version: "0" });
    await c.connect(ct);
    const res = await c.callTool({ name: "get_order", arguments: { id: "6496679971677798670" } });
    assert.equal(res.isError, false);
    assert.equal(res.structuredContent.tracking_number, "SF1");
    const q = Object.fromEntries(new URL(log[0].url).searchParams);
    assert.equal(q.timestamp, "2026-09-25 10:00:00");
    assert.equal(q.param_json, '{"shop_order_id":"6496679971677798670"}');
    const signed = Object.keys(q).filter((k) => !["sign", "access_token", "sign_method"].includes(k)).sort();
    const payload = CREDS.app_secret + signed.map((k) => k + q[k]).join("") + CREDS.app_secret;
    assert.equal(q.sign, crypto.createHmac("sha256", CREDS.app_secret).update(payload).digest("hex"));
    assert.equal(q.access_token, CREDS.access_token);
  } finally { Date.now = realNow; }
});
