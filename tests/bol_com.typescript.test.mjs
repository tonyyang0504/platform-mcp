import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/bol_com.json", import.meta.url), "utf8"));
const VND = "application/vnd.retailer.v10+json";
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => JSON.stringify(r.body ?? {}) }; };

process.env.PLATFORM_MCP_BOL_COM_CLIENT_ID = "bol-client-1";
process.env.PLATFORM_MCP_BOL_COM_CLIENT_SECRET = "BOLSECRETvalue";

async function connect(handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("bol_com: token then vendor media type stock update (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => {
    seen.push({ url, init });
    if (url.href === "https://login.bol.com/token") return { body: { access_token: "JWT-abc", expires_in: 299 } };
    return { status: 202, body: { processStatusId: "1", status: "PENDING" } };
  });
  const res = await client.callTool({ name: "set_inventory", arguments: { listing_id: "off-1", quantity: 12 } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].init.headers.Authorization, "Basic " + Buffer.from("bol-client-1:BOLSECRETvalue").toString("base64"));
  const put = seen.find((s) => s.url.pathname === "/retailer/offers/off-1/stock");
  assert.equal(put.init.headers.Authorization, "Bearer JWT-abc");
  assert.equal(put.init.headers["Content-Type"], VND);
  assert.deepEqual(JSON.parse(put.init.body), { amount: 12, managedByRetailer: false });
});
