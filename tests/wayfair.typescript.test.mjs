import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/wayfair.json", import.meta.url), "utf8"));

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { client_id: "wf_cid", client_secret: "wf_sec", supplier_id: "199492" }, 50, "test", fakeFetch(handler), SPEC.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("wayfair: JSON token request then inventory mutation (wire)", async () => {
  const calls = [];
  const client = await connect((url, init) => {
    calls.push({ url, init });
    if (url.hostname === "sso.auth.wayfair.com") return { body: { access_token: "AT", expires_in: 86400 } };
    return { body: { data: { inventory: { save: { handle: "h", status: "PROCESSING", errors: [] } } } } };
  });
  const res = await client.callTool({ name: "set_inventory", arguments: { sku: "PART-A", quantity: 3 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "PROCESSING");
  assert.deepEqual(JSON.parse(calls[0].init.body), { grant_type: "client_credentials", audience: "https://api.wayfair.com/", client_id: "wf_cid", client_secret: "wf_sec" });
  const last = calls.at(-1);
  assert.equal(last.url.href, "https://api.wayfair.com/v1/graphql");
  assert.equal(last.init.headers.Authorization, "Bearer AT");
  assert.deepEqual(JSON.parse(last.init.body).variables, { inventory: [{ supplierId: 199492, supplierPartNumber: "PART-A", quantityOnHand: 3 }], feedKind: "DIFFERENTIAL" });
});
