import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/vinted_pro.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => JSON.stringify(r.body ?? {}) }; };

process.env.PLATFORM_MCP_VINTED_PRO_ACCESS_KEY = "foo-access";
process.env.PLATFORM_MCP_VINTED_PRO_SIGNING_KEY = "bar-signing-secret";
process.env.PLATFORM_MCP_VINTED_PRO_API_HOST = "pro.svc.vinted.com";

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("vinted_pro: DELETE items signed as ts.METHOD.path.key.body (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 202, body: { items: [{ accepted: true, item_id: "u1" }] } }; });
  const res = await client.callTool({ name: "end_listing", arguments: { listing_id: "u1" } });
  assert.equal(res.isError, false);
  const m = seen.init.headers["X-Vpi-Hmac-Sha256"].match(/^t=(\d{10}),v1=([0-9a-f]{64})$/);
  assert.ok(m);
  assert.equal(seen.init.headers["X-Vpi-Access-Key"], "foo-access");
  const expected = crypto.createHmac("sha256", "bar-signing-secret").update(`${m[1]}.DELETE.${seen.url.pathname}.foo-access.${seen.init.body}`).digest("hex");
  assert.equal(m[2], expected);
  assert.deepEqual(JSON.parse(seen.init.body), { item_ids: ["u1"] });
});
