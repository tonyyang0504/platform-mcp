import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_suppliers/kaspi_shop_api.json", import.meta.url), "utf8"));

test("get_order sends X-Auth-Token and the code filter (wire)", async () => {
  let seen;
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { token: "T" }, 50, "test", fakeFetch((url, init) => { seen = { url, init }; return { body: { data: [{ type: "orders", id: "u1", attributes: { code: "555", totalPrice: 12000, status: "COMPLETED" } }] } }; }), SPEC.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  const res = await client.callTool({ name: "get_order", arguments: { id: "555" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "COMPLETED");
  assert.equal(seen.init.headers["X-Auth-Token"], "T");
  assert.equal(seen.url.searchParams.get("filter[orders][code]"), "555");
});
