import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/marketplaces/atlassian_marketplace.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { email: "dev@example.com", api_token: "atl-secret-token", vendor_id: "1212" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("atlassian marketplace: list_products reads the vendor's apps (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { count: 1, _embedded: { addons: [{ key: "com.acme.app", name: "Acme", summary: "Does things", status: "public" }] } } }; });
  const res = await client.callTool({ name: "list_products", arguments: {} });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.products[0].id, "com.acme.app");
  assert.equal(res.structuredContent.total, 1);
  assert.equal(seen.url.pathname, "/rest/2/addons/vendor/1212");
  assert.equal(seen.url.searchParams.get("includePrivate"), "true");
  assert.equal(seen.init.headers.Authorization, "Basic " + Buffer.from("dev@example.com:atl-secret-token").toString("base64"));
});
