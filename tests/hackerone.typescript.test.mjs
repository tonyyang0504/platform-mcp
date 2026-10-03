import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/competitions/hackerone.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (r.status === 201 || r.status === 204 ? "" : JSON.stringify(r.body ?? {})) }; };

async function connect(handler, creds = { api_username: "hacker", api_token: "h1-secret-token" }) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, creds, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

const PROGRAM = { id: 9, type: "program", attributes: { handle: "acme", name: "acme", policy: "acme's program policy.", submission_state: "open", started_accepting_at: null } };

test("hackerone: tools (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["discover", "get_competition", "me", "my_entries"]);
});

test("hackerone: discover pages programs with basic auth (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { data: [PROGRAM], links: {} } }; });
  const res = await client.callTool({ name: "discover", arguments: { page: 2, limit: 50 } });
  assert.equal(res.structuredContent.competitions[0].id, "acme");
  assert.equal(seen.url.searchParams.get("page[number]"), "2");
  assert.equal(seen.url.searchParams.get("page[size]"), "50");
  const auth = seen.init.headers.Authorization ?? seen.init.headers.authorization;
  assert.ok(auth.startsWith("Basic "));
});

test("hackerone: my_entries map reports (wire)", async () => {
  const client = await connect(() => ({ body: { data: [{ id: "3", attributes: { state: "new", created_at: "2016-02-02T04:05:06.000Z" }, relationships: { program: { data: { attributes: { handle: "teamy" } } } } }] } }));
  const res = await client.callTool({ name: "my_entries", arguments: {} });
  assert.equal(res.structuredContent.entries[0].competition_id, "teamy");
  assert.equal(res.structuredContent.entries[0].status, "new");
});
