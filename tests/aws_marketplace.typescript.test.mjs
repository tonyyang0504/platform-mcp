import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => ({ "content-type": "application/json" })[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/marketplaces/aws_marketplace.json", import.meta.url), "utf8"));
const CREDS = { access_key_id: "AKIDMPEXAMPLE", secret_access_key: "mpSecret/EXAMPLE+abcdef", entity_type: "SaaSProduct" };
const AMZ = "20260925T020000Z";

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", fakeFetch(handler), a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

function auth(method, host, path, query, body) {
  const h = (x) => crypto.createHash("sha256").update(x).digest("hex");
  const scope = `${AMZ.slice(0, 8)}/us-east-1/aws-marketplace/aws4_request`;
  const toSign = ["AWS4-HMAC-SHA256", AMZ, scope, h([method, path, query, `host:${host}\nx-amz-date:${AMZ}\n`, "host;x-amz-date", h(body)].join("\n"))].join("\n");
  let k = Buffer.from("AWS4" + CREDS.secret_access_key);
  for (const p of [AMZ.slice(0, 8), "us-east-1", "aws-marketplace", "aws4_request"]) k = crypto.createHmac("sha256", k).update(p).digest();
  return `AWS4-HMAC-SHA256 Credential=${CREDS.access_key_id}/${scope}, SignedHeaders=host;x-amz-date, Signature=${crypto.createHmac("sha256", k).update(toSign).digest("hex")}`;
}

test("aws_marketplace: ListEntities and SearchAgreements are SigV4-signed per host (wire)", async () => {
  const realNow = Date.now; Date.now = () => 1790301600000;
  try {
    const log = [];
    const client = await connect((url, init) => { log.push({ url, init });
      return url.host.startsWith("catalog") ? { body: { EntitySummaryList: [{ EntityId: "prod-abc123", Name: "Acme SaaS", Visibility: "Public" }], NextToken: "NT-2" } }
        : { body: { agreementViewSummaries: [{ agreementId: "agmt-111", status: "ACTIVE", proposalSummary: { resources: [{ id: "prod-abc123" }] } }] } }; });
    const p = await client.callTool({ name: "list_products", arguments: { limit: 10 } });
    assert.equal(p.structuredContent.products[0].id, "prod-abc123"); assert.equal(p.structuredContent.next_cursor, "NT-2");
    assert.equal(log[0].init.headers.Authorization, auth("POST", "catalog.marketplace.us-east-1.amazonaws.com", "/ListEntities", "", log[0].init.body));
    const s = await client.callTool({ name: "list_sales", arguments: {} });
    assert.equal(s.structuredContent.sales[0].product_id, "prod-abc123");
    assert.equal(log[1].url.host, "agreement-marketplace.us-east-1.amazonaws.com");
    assert.equal(log[1].init.headers["X-Amz-Target"], "AWSMPCommerceService_v20200301.SearchAgreements");
    assert.equal(log[1].init.headers.Authorization, auth("POST", "agreement-marketplace.us-east-1.amazonaws.com", "/", "", log[1].init.body));
  } finally { Date.now = realNow; }
});

test("aws_marketplace: DescribeEntity maps the details document", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { EntityIdentifier: "prod-abc123@7", DetailsDocument: { Description: { ProductTitle: "Acme SaaS" } } } }; });
  const res = await client.callTool({ name: "get_product", arguments: { product_id: "prod-abc123" } });
  assert.equal(res.structuredContent.name, "Acme SaaS"); assert.equal(seen.searchParams.get("entityId"), "prod-abc123");
});
