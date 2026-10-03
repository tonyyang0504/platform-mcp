import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/falabella.json", import.meta.url), "utf8"));
const xmlFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "text/xml" : null) }, text: async () => r.text }; };

process.env.PLATFORM_MCP_FALABELLA_API_KEY = "fal-key-123";
process.env.PLATFORM_MCP_FALABELLA_USER_ID = "seller@example.com";
process.env.PLATFORM_MCP_FALABELLA_OPERATOR_CODE = "facl";

const OK = '<?xml version="1.0" encoding="UTF-8"?><SuccessResponse><Head><RequestId>f8bf8d09</RequestId><RequestAction>ProductUpdate</RequestAction></Head><Body/></SuccessResponse>';
const ORDERS = '<?xml version="1.0"?><SuccessResponse><Head><TotalCount>1</TotalCount></Head><Body><Orders><Order><OrderId>1104089001</OrderId><CreatedAt>2025-04-03 12:00:00</CreatedAt></Order></Orders></Body></SuccessResponse>';

async function connect(handler) {
  globalThis.fetch = xmlFetch(handler);
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

function checkSig(url) {
  const raw = url.search.slice(1);
  const i = raw.lastIndexOf("&Signature=");
  const signed = raw.slice(0, i);
  const names = signed.split("&").map((p) => p.split("=")[0]);
  assert.deepEqual(names, [...names].sort());
  assert.equal(raw.slice(i + 11), crypto.createHmac("sha256", "fal-key-123").update(signed).digest("hex"));
}

test("falabella: list_orders signs the sorted query and parses a single-order XML answer (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { text: ORDERS }; });
  const res = await client.callTool({ name: "list_orders", arguments: { since: "2025-04-01", status: "pending" } });
  assert.equal(res.isError, false);
  assert.deepEqual(res.structuredContent.orders.map((o) => o.id), ["1104089001"]);
  assert.equal(seen.searchParams.get("Action"), "GetOrders");
  assert.equal(seen.searchParams.get("UserID"), "seller@example.com");
  checkSig(seen);
});

test("falabella: update_listing sends a ProductUpdate XML feed (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { text: OK }; });
  const res = await client.callTool({ name: "update_listing", arguments: { listing_id: "SKU-1", price: 59990 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "feed_queued");
  assert.equal(seen.init.body, '<?xml version="1.0" encoding="UTF-8"?><Request><Product><SellerSku>SKU-1</SellerSku><BusinessUnits><BusinessUnit><OperatorCode>facl</OperatorCode><Price>59990</Price></BusinessUnit></BusinessUnits></Product></Request>');
  checkSig(seen.url);
});

test("falabella: ErrorResponse is an error (wire)", async () => {
  const client = await connect(() => ({ text: '<?xml version="1.0"?><ErrorResponse><Head><ErrorCode>1000</ErrorCode><ErrorMessage>Format Error Detected</ErrorMessage></Head></ErrorResponse>' }));
  const res = await client.callTool({ name: "end_listing", arguments: { listing_id: "SKU-1" } });
  assert.equal(res.isError, true);
});
