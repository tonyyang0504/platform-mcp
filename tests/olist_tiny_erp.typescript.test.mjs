import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/olist_tiny_erp.json", import.meta.url), "utf8"));

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { client_id: "tiny-app", client_secret: "tiny-secret-0123456789", refresh_token: "tiny-refresh-aaaaaaaa" }, 50, "test", fakeFetch(handler), a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("olist_tiny_erp: refresh-token grant then bearer product search (wire)", async () => {
  const calls = [];
  const client = await connect((url, init) => {
    calls.push({ url, init });
    if (url.hostname === "accounts.tiny.com.br") return { body: { access_token: "tiny-access-1234567", expires_in: 14400 } };
    return { body: { itens: [{ id: 337, sku: "CAM-01", descricao: "Camiseta", precos: { preco: 49.9 } }], paginacao: { total: 1 } } };
  });
  const res = await client.callTool({ name: "list_products", arguments: { query: "camiseta" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.products[0].id, "337");
  const [tok, api] = calls;
  assert.equal(tok.url.pathname, "/realms/tiny/protocol/openid-connect/token");
  const form = new URLSearchParams(tok.init.body);
  assert.equal(form.get("grant_type"), "refresh_token");
  assert.equal(form.get("client_id"), "tiny-app");
  assert.equal(api.url.pathname, "/public-api/v3/produtos");
  assert.equal(api.url.searchParams.get("nome"), "camiseta");
  assert.equal(api.init.headers.Authorization, "Bearer tiny-access-1234567");
});

test("olist_tiny_erp: purchase order maps to get_order", async () => {
  const client = await connect((url) => url.hostname === "accounts.tiny.com.br" ? { body: { access_token: "tiny-access-1234567", expires_in: 14400 } }
    : { body: { id: 88, numeroPedido: "OC-12", data: "2026-09-01", situacao: "0", totalPedidoCompra: 998 } });
  const res = await client.callTool({ name: "get_order", arguments: { id: "88" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.total, 998);
});
