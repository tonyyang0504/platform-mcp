import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/eu_funding.json", import.meta.url), "utf8"));
const jsonResp = (status, body) => ({ status, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null) }, text: async () => JSON.stringify(body) });
const HIT = { summary: "S", metadata: { identifier: ["HORIZON-CL4-2024-DIGITAL-EMERGING-01-22"], title: ["Fundamentals of Software Engineering (RIA)"], status: ["31094502"] } };

async function connect(log) {
  const a = SPEC.adapter;
  const f = async (url, init) => { log.push({ url, init }); return jsonResp(200, { totalResults: 1, results: [HIT] }); };
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, {}, 50, "test", f, a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("eu_funding: search sends the 'query' and 'languages' parts as application/json (wire)", async () => {
  const log = [];
  const c = await connect(log);
  const res = await c.callTool({ name: "search_postings", arguments: { query: "software", limit: 10 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.postings[0].id, "HORIZON-CL4-2024-DIGITAL-EMERGING-01-22");
  const u = new URL(log[0].url);
  assert.equal(u.searchParams.get("apiKey"), "SEDIA"); assert.equal(u.searchParams.get("text"), "software"); assert.equal(u.searchParams.get("pageSize"), "10");
  const q = log[0].init.body.get("query");
  assert.equal(q.type, "application/json");
  assert.deepEqual(JSON.parse(await q.text()).bool.must[1], { terms: { status: ["31094501", "31094502"] } });
  const l = log[0].init.body.get("languages");
  assert.equal(l.type, "application/json"); assert.deepEqual(JSON.parse(await l.text()), ["en"]);
});

test("eu_funding: get_posting searches the quoted identifier", async () => {
  const log = [];
  const c = await connect(log);
  const res = await c.callTool({ name: "get_posting", arguments: { id: "HORIZON-CL4-2024-DIGITAL-EMERGING-01-22" } });
  assert.equal(res.structuredContent.title, "Fundamentals of Software Engineering (RIA)");
  assert.equal(new URL(log[0].url).searchParams.get("text"), '"HORIZON-CL4-2024-DIGITAL-EMERGING-01-22"');
});
