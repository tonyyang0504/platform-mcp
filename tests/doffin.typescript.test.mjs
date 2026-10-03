import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/doffin.json", import.meta.url), "utf8"));
const KEY = "doffin-sub-key-0123456789abcdef";
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const HIT = { id: "2026-105123", buyer: [{ id: "b1", organizationId: "974760673", name: "Statens vegvesen" }], heading: "Vedlikehold av riksvei", estimatedValue: { currencyCode: "NOK", amount: 25000000 }, publicationDate: "2026-09-20", deadline: "2026-10-30T12:00:00Z", cpvCodes: ["45233141"] };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { subscription_key: KEY }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

const hdr = (init, name) => { const h = init.headers ?? {}; if (typeof h.get === "function") return h.get(name); const k = Object.keys(h).find((x) => x.toLowerCase() === name.toLowerCase()); return k ? h[k] : undefined; };

test("doffin: search sends the APIM key header and maps hits (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { numHitsTotal: 57, hits: [HIT] } }; });
  const res = await client.callTool({ name: "search_postings", arguments: { query: "riksvei", min_budget: 1000000, limit: 10 } });
  assert.equal(res.isError, false);
  assert.equal(seen.url.origin + seen.url.pathname, "https://api.doffin.no/public/v2/search");
  assert.equal(hdr(seen.init, "Ocp-Apim-Subscription-Key"), KEY);
  assert.equal(seen.url.searchParams.get("searchString"), "riksvei");
  assert.equal(seen.url.searchParams.get("estimatedValueFrom"), "1000000");
  assert.equal(seen.url.searchParams.get("status"), "ACTIVE");
  const p = res.structuredContent.postings[0];
  assert.equal(p.buyer, "Statens vegvesen");
  assert.equal(p.budget_max, 25000000);
  assert.equal(res.structuredContent.total, 57);
});

test("doffin: 401 is auth_error and the key is scrubbed (wire)", async () => {
  const client = await connect(() => ({ status: 401, body: { statusCode: 401, message: `invalid subscription key ${KEY}` } }));
  const res = await client.callTool({ name: "search_postings", arguments: { query: "vei" } });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.ok(!JSON.stringify(res).includes(KEY));
});
