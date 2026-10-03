import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/bookvault.json", import.meta.url), "utf8"));

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_key: "bv_k" }, 50, "test", fakeFetch(handler), SPEC.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("get_order loads by PodRef and maps tracking (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: {
    identification: { podRef: "123456", docRef: "abc" }, metadata: { status: "Dispatched", dateCreated: "2026-09-01T10:00:00", partner: { currency: "GBP" } },
    financials: { orderCost: { grandTotal: 12.34 } }, fulfillment: { trackingDetails: { tracked: true, trackingNumber: "RM1", combinedURL: "https://track/RM1" } } } }; });
  const res = await client.callTool({ name: "get_order", arguments: { id: "123456" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "Dispatched");
  assert.equal(res.structuredContent.total, 12.34);
  assert.equal(res.structuredContent.tracking_number, "RM1");
  assert.equal(seen.url.pathname, "/v4/order");
  assert.equal(seen.url.searchParams.get("type"), "PodRef");
  assert.equal(seen.url.searchParams.get("value"), "123456");
  assert.equal(seen.init.headers.Authorization, "basic bv_k");
});
