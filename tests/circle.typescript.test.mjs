import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/marketplaces/circle.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler, creds = { admin_token: "circle_test_secret" }) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("circle: only the charge side of the marketplaces vocabulary is served (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["list_refunds", "list_sales", "me", "refund"]);
  const rf = tools.find((t) => t.name === "refund");
  assert.equal(rf.annotations.readOnlyHint, false);
  assert.equal(rf.annotations.destructiveHint, true);
  assert.deepEqual(rf.inputSchema.required, ["sale_id"]);
  assert.equal(tools.find((t) => t.name === "list_sales")._meta["platform_mcp/endpoint"], "/api/admin/v2/community_member_charges");
  assert.equal(tools.find((t) => t.name === "me").annotations.readOnlyHint, true);
});

test("circle: list_sales pages the charges and maps the record with count as total (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { page: 2, per_page: 1, has_next_page: true, count: 3, page_count: 3, records: [{ id: 1, status: "paid", amount: 1000, amount_refunded: 0, currency: "usd", created_at: "2021-01-01T00:00:00Z", paywall_id: 7, paywall_name: "Premium Membership", community_member_email: "jane@example.com" }] } }; });
  const res = await client.callTool({ name: "list_sales", arguments: { product_id: "7", since: "2020-12-01T00:00:00Z", page: 2, limit: 1 } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.origin + seen.url.pathname, "https://app.circle.so/api/admin/v2/community_member_charges");
  assert.equal(seen.url.searchParams.get("page"), "2");
  assert.equal(seen.url.searchParams.get("per_page"), "1");
  assert.equal(seen.url.searchParams.get("paywall_ids"), "7");
  assert.equal(seen.url.searchParams.get("created_at_gte"), "2020-12-01T00:00:00Z");
  assert.equal(seen.init.headers.Authorization, "Bearer circle_test_secret");
  const s = res.structuredContent.sales[0];
  assert.equal(s.id, "1");
  assert.equal(s.product_id, "7");
  assert.equal(s.product_name, "Premium Membership");
  assert.equal(s.amount, 1000);
  assert.equal(s.customer_email, "jane@example.com");
  assert.equal(res.structuredContent.total, 3);
  assert.equal(res.structuredContent.next_page, 3);
});

test("circle: refund posts the subunit amount and the required reason_details (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { id: 1, status: "partial_refunded", amount: 1000, amount_refunded: 200, currency: "usd", created_at: "2021-01-01T00:00:00Z" } }; });
  const res = await client.callTool({ name: "refund", arguments: { sale_id: "1", amount: 200, reason: "duplicate charge" } });
  assert.equal(res.isError, false);
  assert.equal(seen.init.method, "POST");
  assert.equal(seen.url.pathname, "/api/admin/v2/community_member_charges/1/refund");
  assert.deepEqual(JSON.parse(seen.init.body), { amount: 200, reason_details: "duplicate charge" });
  assert.equal(seen.init.headers.Authorization, "Bearer circle_test_secret");
  assert.equal(res.structuredContent.sale_id, "1");
  assert.equal(res.structuredContent.amount, 200);
  assert.equal(res.structuredContent.status, "partial_refunded");
});

test("circle: refused token is an auth_error result without the secret (wire)", async () => {
  const client = await connect(() => ({ status: 401, body: { success: false, message: "Invalid token=circle_test_secret" } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.equal(JSON.stringify(res.structuredContent).includes("circle_test_secret"), false);
});
