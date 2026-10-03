import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/market_data/openfigi.json", import.meta.url), "utf8"));
const resp = (status, body, type = "application/json") => ({ status, headers: { get: (k) => (k.toLowerCase() === "content-type" && body !== undefined ? type : null) }, text: async () => (body === undefined ? "" : typeof body === "string" ? body : JSON.stringify(body)) });

async function connect(creds, handler) {
  const log = [];
  const fetcher = async (url, init) => { log.push({ url: new URL(url), init }); const r = handler(new URL(url), init, log.length); return resp(r.status ?? 200, r.body, r.type); };
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...creds }, 50, "test", fetcher, a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return { client, log };
}
const hdr = (init, name) => { const h = init.headers ?? {}; const k = Object.keys(h).find((x) => x.toLowerCase() === name.toLowerCase()); return k ? h[k] : undefined; };

test("openfigi search posts query/start and returns next as next_cursor (wire)", async () => {
  const { client, log } = await connect({ api_key: "k-123456789" }, (_u, _i, n) => (n === 1
    ? { body: { data: [{ figi: "BBG000BLNNH6", name: "INTL BUSINESS MACHINES CORP", ticker: "IBM", securityType: "Common Stock" }], next: "CUR1" } }
    : { body: { data: [] } }));
  const r1 = (await client.callTool({ name: "search_symbols", arguments: { query: "ibm" } })).structuredContent;
  assert.deepEqual([r1.results[0].symbol, r1.results[0].type, r1.next_cursor, r1.next_page], ["BBG000BLNNH6", "Common Stock", "CUR1", null]);
  assert.deepEqual(JSON.parse(log[0].init.body), { query: "ibm" });
  assert.equal(hdr(log[0].init, "X-OPENFIGI-APIKEY"), "k-123456789");
  const r2 = (await client.callTool({ name: "search_symbols", arguments: { query: "ibm", cursor: "CUR1" } })).structuredContent;
  assert.deepEqual(JSON.parse(log[1].init.body), { query: "ibm", start: "CUR1" });
  assert.equal(r2.next_cursor, null);
});

const HUNDRED = { data: Array.from({ length: 100 }, (_, i) => ({ figi: `BBG${String(i).padStart(9, "0")}`, name: `N${i}`, securityType: "Common Stock" })), next: "CUR1" };
const ids = (from, to) => Array.from({ length: to - from }, (_, i) => `BBG${String(from + i).padStart(9, "0")}`);

test("openfigi fixed 100-row pages are trimmed to limit with cursors that walk the rest (wire)", async () => {
  const { client, log } = await connect({}, (_u, _i, n) => (n === 1 ? { body: HUNDRED } : { body: { data: [{ figi: "BBGNEXT", name: "x" }] } }));
  const p1 = (await client.callTool({ name: "search_symbols", arguments: { query: "ibm", limit: 40 } })).structuredContent;
  assert.deepEqual([p1.results.map((r) => r.symbol), p1.next_cursor, p1.next_page], [ids(0, 40), "pmc1.W251bGwsNDBd", null]);
  const p2 = (await client.callTool({ name: "search_symbols", arguments: { query: "ibm", limit: 40, cursor: p1.next_cursor } })).structuredContent;
  assert.deepEqual([p2.results.map((r) => r.symbol), p2.next_cursor], [ids(40, 80), "pmc1.W251bGwsODBd"]);
  const p3 = (await client.callTool({ name: "search_symbols", arguments: { query: "ibm", limit: 40, cursor: p2.next_cursor } })).structuredContent;
  assert.deepEqual([p3.results.map((r) => r.symbol), p3.next_cursor], [ids(80, 100), "CUR1"]);
  assert.equal(log.length, 1); // one search served three windows
  const p4 = (await client.callTool({ name: "search_symbols", arguments: { query: "ibm", limit: 40, cursor: "CUR1" } })).structuredContent;
  assert.deepEqual([p4.results.map((r) => r.symbol), p4.next_cursor], [["BBGNEXT"], null]);
  assert.deepEqual(JSON.parse(log[1].init.body), { query: "ibm", start: "CUR1" });
});

test("openfigi window cursor inside a later page resends that page's cursor; a forged cursor is invalid_input (wire)", async () => {
  const { client, log } = await connect({}, () => ({ body: HUNDRED }));
  const cur = "pmc1." + Buffer.from(JSON.stringify(["CUR0", 90])).toString("base64url");
  const r = (await client.callTool({ name: "search_symbols", arguments: { query: "ibm", limit: 25, cursor: cur } })).structuredContent;
  assert.deepEqual(JSON.parse(log[0].init.body), { query: "ibm", start: "CUR0" });
  assert.deepEqual([r.results.map((x) => x.symbol), r.next_cursor], [ids(90, 100), "CUR1"]);
  const bad = await client.callTool({ name: "search_symbols", arguments: { query: "ibm", cursor: "pmc1.!!notbase64" } });
  assert.deepEqual([bad.isError, bad.structuredContent.error], [true, "invalid_input"]);
});
