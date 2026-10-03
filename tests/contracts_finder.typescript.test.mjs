import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/contracts_finder.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

const RELEASE = {
  ocid: "ocds-b5fd17-1a2b3c", id: "ocds-b5fd17-1a2b3c-2026-09-20T10:00:00Z", language: "en", date: "2026-09-20T10:00:00Z", tag: ["tender"],
  tender: { id: "t1", title: "Provision of cloud hosting", description: "Managed hosting.", status: "active", value: { amount: 250000, currency: "GBP" }, tenderPeriod: { endDate: "2026-10-30T12:00:00Z" } },
  buyer: { name: "Example Borough Council" },
};

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, {}, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("contracts_finder: search and details only (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_posting", "search_postings"]);
  assert.ok(tools.every((t) => t.annotations.readOnlyHint === true));
  assert.deepEqual(tools.find((t) => t.name === "get_posting").inputSchema.required, ["id"]);
});

test("contracts_finder: search fixes stages=tender and maps OCDS releases (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { uri: "x", version: "1.1", publishedDate: "2026-09-24T09:00:00Z", releases: [RELEASE] } }; });
  const res = await client.callTool({ name: "search_postings", arguments: { limit: 10 } });
  assert.equal(res.isError, false);
  const p = res.structuredContent.postings[0];
  assert.equal(p.id, "ocds-b5fd17-1a2b3c-2026-09-20T10:00:00Z"); // the release id get_posting accepts
  assert.equal(p.raw.ocid, "ocds-b5fd17-1a2b3c");
  assert.equal(p.title, "Provision of cloud hosting");
  assert.equal(p.buyer, "Example Borough Council");
  assert.equal(p.budget_max, 250000);
  assert.equal(p.currency, "GBP");
  assert.equal(p.deadline, "2026-10-30T12:00:00Z");
  assert.equal(seen.pathname, "/Published/Notices/OCDS/Search");
  assert.equal(seen.searchParams.get("stages"), "tender");
  assert.equal(seen.searchParams.get("limit"), "10");
});

test("contracts_finder: get_posting reads releases[0] of the release package (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { uri: "x", releases: [RELEASE] } }; });
  const res = await client.callTool({ name: "get_posting", arguments: { id: RELEASE.id } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.title, "Provision of cloud hosting");
  assert.equal(seen.pathname, `/Published/OCDS/Release/${RELEASE.id}`);
});

test("contracts_finder: 403 rate-limit answer is an isError result (wire)", async () => {
  const client = await connect(() => ({ status: 403, body: { message: "rate limit" } }));
  const res = await client.callTool({ name: "search_postings", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited"); // 403 with rate-limit wording (forge stress test 2026-10)
});
