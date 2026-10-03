import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/bling_erp.json", import.meta.url), "utf8"));
const TOKEN_URL = "https://api.bling.com.br/Api/v3/oauth/token";
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const tokenOk = { body: { access_token: "acc-1", expires_in: 21600, token_type: "Bearer", refresh_token: "rtSECRET2" } };
delete process.env.PLATFORM_MCP_STATE_DIR;

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { client_id: "cid", client_secret: "csecretVALUE", refresh_token: "rtSECRET1" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_order", "get_product", "list_products", "me"]);
});

test("refresh with Basic client auth, then bearer on /produtos (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => { seen.push({ url, init }); return url.href === TOKEN_URL ? tokenOk : { body: { data: [{ id: 1, nome: "Copo", codigo: "C-1", preco: 4.99 }] } }; });
  const res = await client.callTool({ name: "list_products", arguments: { query: "Copo", page: 1, limit: 5 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.products[0].title, "Copo");
  const tok = seen.find((s) => s.url.href === TOKEN_URL);
  assert.equal(new URLSearchParams(tok.init.body).get("grant_type"), "refresh_token");
  assert.equal(tok.init.headers.Authorization ?? tok.init.headers.authorization, "Basic " + Buffer.from("cid:csecretVALUE").toString("base64"));
  const api = seen.find((s) => s.url.pathname === "/Api/v3/produtos");
  assert.equal(api.url.searchParams.get("nome"), "Copo");
  assert.equal(api.init.headers.Authorization, "Bearer acc-1");
});

test("refused refresh is an auth error without secrets (wire)", async () => {
  const client = await connect(() => ({ status: 400, body: { error: { type: "invalid_grant", message: "bad rtSECRET1" } } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.equal(JSON.stringify(res.structuredContent).includes("rtSECRET1"), false);
});
