import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/lulu_print_api.json", import.meta.url), "utf8"));
const TOKEN_URL = "https://api.lulu.com/auth/realms/glasstree/protocol/openid-connect/token";
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const tokenOk = { body: { access_token: "eyJ.acc", expires_in: 3600, token_type: "Bearer" } };

async function connect(handler, creds = { client_id: "ck", client_secret: "csSECRET" }) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["create_order", "get_order", "me", "track"]);
});

test("get_order mints a token and maps the print job (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => { seen.push({ url, init }); return url.href === TOKEN_URL ? tokenOk : { body: { id: 7, status: { name: "UNPAID", message: "needs to be paid" }, costs: { currency: "USD", total_cost_incl_tax: "86.45" }, date_created: "2017-08-07T08:47:26Z", line_items: [] } }; });
  const res = await client.callTool({ name: "get_order", arguments: { id: "7" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "UNPAID");
  assert.equal(res.structuredContent.total_incl_tax, "86.45");
  const tok = seen.find((s) => s.url.href === TOKEN_URL);
  assert.equal(new URLSearchParams(tok.init.body).get("grant_type"), "client_credentials");
  const api = seen.find((s) => s.url.pathname === "/print-jobs/7/");
  assert.equal(api.init.headers.Authorization, "Bearer eyJ.acc");
});

test("create_order sends shipping_level and contact_email (wire)", async () => {
  let body;
  const client = await connect((url, init) => { if (url.href === TOKEN_URL) return tokenOk; body = JSON.parse(init.body); return { status: 201, body: { id: 9, status: { name: "CREATED" } } }; }, { client_id: "ck", client_secret: "csSECRET", contact_email: "ops@example.com" });
  const res = await client.callTool({ name: "create_order", arguments: { items: [{ printable_id: "48efe280", quantity: 1 }], shipping_address: { name: "A", country_code: "US" }, shipping_option: "GROUND" } });
  assert.equal(res.isError, false);
  assert.equal(body.shipping_level, "GROUND");
  assert.equal(body.contact_email, "ops@example.com");
  assert.deepEqual(body.line_items, [{ printable_id: "48efe280", quantity: 1 }]);
});
