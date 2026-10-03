import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/market_data/macro_collector.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_key: "abcdefghijklmnopqrstuvwxyz123456" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("macro_collector: tools follow the market_data vocabulary (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_series", "me", "search_symbols"]);
  const gs = tools.find((t) => t.name === "get_series");
  assert.equal(gs.annotations.readOnlyHint, true);
  assert.deepEqual(gs.inputSchema.required, ["series_id"]);
  assert.equal(gs._meta["platform_mcp/endpoint"], "/fred/series/observations");
});

test("macro_collector: get_series sends api_key + file_type=json and maps observations (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { count: 1, offset: 0, limit: 100000, observations: [{ realtime_start: "2026-09-24", realtime_end: "2026-09-24", date: "2026-01-01", value: "4.33" }] } }; });
  const res = await client.callTool({ name: "get_series", arguments: { series_id: "FEDFUNDS", start: "2026-01-01", end: "2026-03-01" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.points[0].time, "2026-01-01");
  assert.equal(res.structuredContent.points[0].value, "4.33");
  assert.equal(seen.pathname, "/fred/series/observations");
  assert.equal(seen.searchParams.get("series_id"), "FEDFUNDS");
  assert.equal(seen.searchParams.get("observation_start"), "2026-01-01");
  assert.equal(seen.searchParams.get("observation_end"), "2026-03-01");
  assert.equal(seen.searchParams.get("file_type"), "json");
  assert.equal(seen.searchParams.get("api_key"), "abcdefghijklmnopqrstuvwxyz123456");
});

test("macro_collector: search_symbols maps seriess with offset paging (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { count: 32, offset: 10, limit: 10, seriess: [{ id: "MSIM2", title: "Monetary Services Index: M2 (preferred)", frequency: "Monthly", units: "Billions of Dollars" }] } }; });
  const res = await client.callTool({ name: "search_symbols", arguments: { query: "monetary", limit: 10, page: 2 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.results[0].symbol, "MSIM2");
  assert.equal(res.structuredContent.results[0].type, "Monthly");
  assert.equal(res.structuredContent.total, 32);
  assert.equal(seen.searchParams.get("search_text"), "monetary");
  assert.equal(seen.searchParams.get("offset"), "10");
});

test("macro_collector: 400 bad key is an isError result without the key in the message (wire)", async () => {
  const client = await connect(() => ({ status: 400, body: { error_code: 400, error_message: "Bad Request.  Variable api_key is not set." } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.ok(!JSON.stringify(res.structuredContent).includes("abcdefghijklmnopqrstuvwxyz123456"));
});
