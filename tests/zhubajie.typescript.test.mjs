import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/marketplaces/zhubajie.json", import.meta.url), "utf8"));
const CREDS = { app_key: "2016061718xxxxxx001", app_secret: "00A583ED7F8D", access_token: "ab4ce091", openid: "7DB78F3D" };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, CREDS, 50, "test", fakeFetch(handler), SPEC.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("zhubajie: list_products signs the router call (SHA1 secret-wrapped, sorted params)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { total: 1, serviceList: [{ serviceId: 1001966264, subject: "LOGO", amount: 100, state: 2 }] } }; });
  const res = await client.callTool({ name: "list_products", arguments: { limit: 10 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.products[0].id, "1001966264");
  assert.equal(res.structuredContent.products[0].currency, "CNY");
  const q = Object.fromEntries(seen.searchParams);
  const payload = CREDS.app_secret + Object.keys(q).filter((k) => k !== "sign").sort().map((k) => k + q[k]).join("") + CREDS.app_secret;
  assert.equal(q.sign, createHash("sha1").update(payload).digest("hex").toUpperCase());
  assert.equal(q.method, "zbj.service.getServiceList");
  assert.equal(q.state, "1");
  assert.equal(q.openid, CREDS.openid);
});

test("zhubajie: list_sales sends startTime as yyyyMMddHHmmss; error envelope fails", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return url.searchParams.get("method") === "zbj.trade.getRefundList"
    ? { body: { errorToken: "@@$-ERROR_TOKEN$-@@", code: "9", message: "业务逻辑出错" } }
    : { body: { total: 1, tradeInfos: [{ taskId: 7557549, title: "T", amount: 100 }] } }; });
  const res = await client.callTool({ name: "list_sales", arguments: { since: "2026-09-01" } });
  assert.equal(res.structuredContent.sales[0].id, "7557549");
  assert.equal(seen.searchParams.get("startTime"), "20260901000000");
  const bad = await client.callTool({ name: "list_refunds", arguments: {} });
  assert.equal(bad.isError, true);
});
