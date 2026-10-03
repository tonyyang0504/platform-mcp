import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/competitions/freelancer.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (r.status === 201 || r.status === 204 ? "" : JSON.stringify(r.body ?? {})) }; };

async function connect(handler, creds = { access_token: "fl-token" }) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

const CONTEST = { id: 2790072, title: "Modern Navy & Orange Logo", prize: 100.0, description: "I'm re-branding", status: "active", type: "guaranteed" };

test("freelancer competitions: tools (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["discover", "get_competition", "me"]);
});

test("freelancer competitions: discover searches active contests (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { status: "success", result: { contests: [CONTEST], total_count: 105 } } }; });
  const res = await client.callTool({ name: "discover", arguments: { query: "logo" } });
  assert.equal(res.structuredContent.competitions[0].id, "2790072");
  assert.equal(res.structuredContent.total, 105);
  assert.equal(seen.url.searchParams.get("query"), "logo");
  assert.equal(seen.init.headers["freelancer-oauth-v1"], "fl-token");
});

test("freelancer competitions: get_competition unwraps the list (wire)", async () => {
  const client = await connect(() => ({ body: { status: "success", result: { contests: [CONTEST] } } }));
  const res = await client.callTool({ name: "get_competition", arguments: { competition_id: "2790072" } });
  assert.equal(res.structuredContent.title, "Modern Navy & Orange Logo");
});
