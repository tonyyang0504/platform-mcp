import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (r.raw ?? JSON.stringify(r.body ?? {})) }; };
async function connect(spec, handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(spec);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}
const body = (init) => JSON.parse(init.body);

const SPEC = JSON.parse(readFileSync(new URL("../catalog/builder_tools/google_sheets.json", import.meta.url), "utf8"));
Object.assign(process.env, {"PLATFORM_MCP_GOOGLE_SHEETS_CLIENT_ID": "gcid", "PLATFORM_MCP_GOOGLE_SHEETS_CLIENT_SECRET": "gsecret", "PLATFORM_MCP_GOOGLE_SHEETS_REFRESH_TOKEN": "1//sheets", "PLATFORM_MCP_GOOGLE_SHEETS_SPREADSHEET_ID": "SHEET1"});

const handler = (seen, reply) => (url, init) => {
  if (url.hostname === "oauth2.googleapis.com") return { body: { access_token: "ya29.SH", expires_in: 3599 } };
  seen.push({ url, init });
  return { body: reply };
};

test("google_sheets create_item: values:append with USER_ENTERED and refreshed bearer (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, handler(seen, { updates: { updatedRange: "Sheet1!A5:B5" } }));
  const res = await client.callTool({ name: "create_item", arguments: { collection: "Sheet1!A1", fields: { values: [["x", 3]] } } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].init.method, "POST");
  assert.equal(decodeURIComponent(seen[0].url.pathname), "/v4/spreadsheets/SHEET1/values/Sheet1!A1:append");
  assert.equal(seen[0].url.searchParams.get("valueInputOption"), "USER_ENTERED");
  assert.equal(seen[0].init.headers.Authorization, "Bearer ya29.SH");
  assert.deepEqual(body(seen[0].init), { values: [["x", 3]] });
  assert.equal(res.structuredContent.id, "Sheet1!A5:B5");
});

test("google_sheets list_items: rows of the range (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, handler(seen, { range: "Sheet1!A1:B2", values: [["a", "b"], ["1", "2"]] }));
  const res = await client.callTool({ name: "list_items", arguments: { collection: "Sheet1!A1:B2" } });
  assert.deepEqual(res.structuredContent.items.map((i) => i.cells), [["a", "b"], ["1", "2"]]);
});
