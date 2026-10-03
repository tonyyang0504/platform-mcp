import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/competitions/topcoder.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (r.status === 201 || r.status === 204 ? "" : JSON.stringify(r.body ?? {})) }; };

async function connect(handler, creds = {}) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

const CH = { id: "6a5da7b6-3841-43cb-ae9d-98416bea0d9d", name: "AI Deal Scoping Assistant", status: "COMPLETED", track: { name: "Development" }, tags: ["AI"], startDate: "2026-09-01T12:00:00.000Z", submissionEndDate: "2026-09-15T12:00:00.000Z", winners: [{ userId: 1, handle: "jaypatel1325", placement: 1 }] };

test("topcoder competitions: public tools (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["discover", "get_competition", "standings"]);
});

test("topcoder competitions: discover maps status and search (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: [CH] }; });
  const res = await client.callTool({ name: "discover", arguments: { query: "ai", status: "open" } });
  assert.equal(res.structuredContent.competitions[0].kind, "Development");
  assert.deepEqual(res.structuredContent.competitions[0].tags, ["AI"]);
  assert.equal(seen.searchParams.get("status"), "Active");
  assert.equal(seen.searchParams.get("search"), "ai");
});

test("topcoder competitions: standings are winners (wire)", async () => {
  const client = await connect(() => ({ body: CH }));
  const res = await client.callTool({ name: "standings", arguments: { competition_id: CH.id } });
  assert.equal(res.structuredContent.standings[0].rank, 1);
  assert.equal(res.structuredContent.standings[0].team, "jaypatel1325");
});
