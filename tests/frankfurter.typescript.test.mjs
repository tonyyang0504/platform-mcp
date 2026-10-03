import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/market_data/frankfurter.json", import.meta.url), "utf8"));
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

const CURRENCIES = [
  { iso_code: "AUD", iso_numeric: "036", name: "Australian Dollar", symbol: "$" },
  { iso_code: "EUR", iso_numeric: "978", name: "Euro", symbol: "\u20ac" },
  { iso_code: "JPY", iso_numeric: "392", name: "Japanese Yen", symbol: "\u00a5" },
  { iso_code: "USD", iso_numeric: "840", name: "United States Dollar", symbol: "$" },
];

test("frankfurter search_symbols filters the currency list by code or name and pages locally (wire)", async () => {
  const { client, log } = await connect({}, () => ({ body: CURRENCIES }));
  const r = await client.callTool({ name: "search_symbols", arguments: { query: "dollar" } });
  assert.equal(r.isError, false);
  assert.deepEqual(r.structuredContent.results.map((x) => [x.symbol, x.name, x.type]), [["AUD", "Australian Dollar", "currency"], ["USD", "United States Dollar", "currency"]]);
  assert.deepEqual([r.structuredContent.total, r.structuredContent.next_page], [2, null]);
  assert.equal(log[0].url.pathname, "/v2/currencies");
  const usd = await client.callTool({ name: "search_symbols", arguments: { query: "usd", limit: 1 } });
  assert.deepEqual(usd.structuredContent.results.map((x) => x.symbol), ["USD"]);
  const p1 = (await client.callTool({ name: "search_symbols", arguments: { query: "a", limit: 2 } })).structuredContent;
  const p2 = (await client.callTool({ name: "search_symbols", arguments: { query: "a", limit: 2, page: 2 } })).structuredContent;
  assert.deepEqual([p1.results.map((x) => x.symbol), p1.next_page, p1.total], [["AUD", "JPY"], 2, 3]);
  assert.deepEqual([p2.results.map((x) => x.symbol), p2.next_page], [["USD"], null]);
  assert.equal(log.length, 1); // fetched once, paged from the short-lived cache
});

test("frankfurter 422 for an unknown quote currency is invalid_input (wire)", async () => {
  const { client } = await connect({}, () => ({ status: 422, body: { status: 422, message: "invalid currency: XXXQ" } }));
  const r = await client.callTool({ name: "get_series", arguments: { series_id: "XXXQ" } });
  assert.deepEqual([r.isError, r.structuredContent.error, r.structuredContent.http_status], [true, "invalid_input", 422]);
  assert.match(r.structuredContent.message, /invalid currency: XXXQ/);
});

test("frankfurter get_series sends quotes/from/to/base and maps rates (wire)", async () => {
  const { client, log } = await connect({ base_currency: "GBP" }, () => ({ body: [{ date: "2026-09-01", base: "GBP", quote: "USD", rate: 1.33 }] }));
  const r = await client.callTool({ name: "get_series", arguments: { series_id: "USD", start: "2026-09-01", end: "2026-09-02" } });
  assert.deepEqual(r.structuredContent.points.map((p) => [p.time, p.value]), [["2026-09-01", 1.33]]);
  const q = log[0].url.searchParams;
  assert.deepEqual([q.get("quotes"), q.get("from"), q.get("to"), q.get("base")], ["USD", "2026-09-01", "2026-09-02", "GBP"]);
  const bad = await client.callTool({ name: "get_series", arguments: { series_id: "USD", start: "01/09/2026" } });
  assert.equal(bad.isError, true);
  assert.equal(bad.structuredContent.error, "invalid_input");
});
