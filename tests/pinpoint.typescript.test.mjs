import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/pinpoint.json", import.meta.url), "utf8"));
const POST = { id: "559663", title: "Founding Legal Counsel", description: "<div>Hi</div>", compensation_minimum: 90000, compensation_maximum: 110000, compensation_currency: "GBP", url: "https://workwithus.pinpointhq.com/en/postings/ce6c9e5c", location: { id: "283", name: "Remote" } };
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (typeof r.body === "string" ? r.body : JSON.stringify(r.body ?? {})) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { company_subdomain: "workwithus" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("search hits the subdomain feed with location_city_state_name (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { data: [POST] } }; });
  const res = await client.callTool({ name: "search", arguments: { query: "legal", location: "London" } });
  assert.equal(res.isError, false);
  assert.equal(seen.origin + seen.pathname, "https://workwithus.pinpointhq.com/postings.json");
  assert.deepEqual([...seen.searchParams.entries()], [["location_city_state_name", "London"]]);
  const p = res.structuredContent.postings[0];
  assert.equal(p.id, "559663");
  assert.equal(p.currency, "GBP");
});

test("upstream failure is isError (wire)", async () => {
  const client = await connect(() => ({ status: 503, body: "maintenance" }));
  const res = await client.callTool({ name: "search", arguments: { query: "x" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "upstream_error");
});
