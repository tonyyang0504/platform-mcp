import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/marketplaces/allegro.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { client_id: "cid", client_secret: "allegro-client-secret", refresh_token: "allegro-refresh-1" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("allegro marketplaces: list_sales reads checkout forms newest first (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => { seen.push({ url, init }); return url.host === "allegro.pl" ? { body: { access_token: "allegro-access-1", expires_in: 43199 } } : { body: { checkoutForms: [{ id: "o-1", status: "READY_FOR_PROCESSING", buyer: { email: "b@x.pl" }, summary: { totalToPay: { amount: "99.00", currency: "PLN" } }, lineItems: [{ boughtAt: "2026-09-01T10:00:00Z", offer: { id: "123", name: "Kubek" } }] }], totalCount: 1 } }; });
  const res = await client.callTool({ name: "list_sales", arguments: { since: "2026-09-01T00:00:00Z" } });
  assert.equal(res.isError, false);
  const s = res.structuredContent.sales[0];
  assert.equal(s.product_id, "123");
  assert.equal(s.amount, "99.00");
  const call = seen.find((x) => x.url.pathname === "/order/checkout-forms");
  assert.equal(call.url.searchParams.get("lineItems.boughtAt.gte"), "2026-09-01T00:00:00Z");
  assert.equal(call.url.searchParams.get("sort"), "-lineItems.boughtAt");
  assert.equal(call.init.headers.Authorization, "Bearer allegro-access-1");
});
