import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/fruugo.json", import.meta.url), "utf8"));
const xmlFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/xml" : null) }, text: async () => r.text }; };

process.env.PLATFORM_MCP_FRUUGO_USERNAME = "shop@example.com";
process.env.PLATFORM_MCP_FRUUGO_PASSWORD = "pw";

async function connect(handler) {
  globalThis.fetch = xmlFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("fruugo: list_orders parses namespaced order XML with Basic auth (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { text: '<?xml version="1.0"?><o:orders xmlns:o="https://www.fruugo.com/orders/schema"><o:order><o:orderId>9135311001000444</o:orderId><o:orderStatus>PENDING</o:orderStatus></o:order><o:order><o:orderId>2</o:orderId><o:orderStatus>PROCESSED</o:orderStatus></o:order></o:orders>' }; });
  const res = await client.callTool({ name: "list_orders", arguments: { since: "2020-11-25" } });
  assert.equal(res.isError, false);
  assert.deepEqual(res.structuredContent.orders.map((o) => [o.id, o.status]), [["9135311001000444", "PENDING"], ["2", "PROCESSED"]]);
  assert.equal(seen.url.searchParams.get("from"), "2020-11-25");
  assert.equal(seen.init.headers.Authorization, "Basic " + Buffer.from("shop@example.com:pw").toString("base64"));
});

test("fruugo: set_inventory posts <skus><sku fruugoSkuId> XML (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = init; return { text: "<skus/>" }; });
  const res = await client.callTool({ name: "set_inventory", arguments: { listing_id: "5146705", quantity: 10 } });
  assert.equal(res.isError, false);
  assert.equal(seen.body, '<?xml version="1.0" encoding="UTF-8"?><skus><sku fruugoSkuId="5146705"><itemsInStock>10</itemsInStock></sku></skus>');
});

test("fruugo: 401 is an auth error (wire)", async () => {
  const client = await connect(() => ({ status: 401, text: "" }));
  const res = await client.callTool({ name: "mark_shipped", arguments: { order_id: "1" } });
  assert.equal(res.isError, true);
});
