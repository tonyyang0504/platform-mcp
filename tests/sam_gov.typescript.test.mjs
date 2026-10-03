import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/sam_gov.json", import.meta.url), "utf8"));
const json = (status, body) => ({ status, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null) }, text: async () => JSON.stringify(body) });
const OPP = { noticeId: "abc123", title: "Historic Office Renovation", fullParentPathName: "GSA.PBS", postedDate: "2026-09-04", responseDeadLine: "2026-10-04T15:00:00-05:00", uiLink: "https://sam.gov/opp/abc123/view" };
const mmddyyyy = (daysAgo) => { const d = new Date(Date.now() - daysAgo * 86400000); return `${String(d.getUTCMonth() + 1).padStart(2, "0")}/${String(d.getUTCDate()).padStart(2, "0")}/${d.getUTCFullYear()}`; };

async function connect(handler) {
  const log = [];
  const fetcher = async (url, init) => { log.push({ url: new URL(url), init }); return handler(); };
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_key: "SAM-KEY-123456" }, 50, "test", fetcher));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  client.log = log;
  return client;
}

test("sam_gov: search_postings sends MM/dd/yyyy window (main, wire)", async () => {
  const client = await connect(() => json(200, { totalRecords: 34, opportunitiesData: [OPP] }));
  const res = await client.callTool({ name: "search_postings", arguments: { query: "renovation", page: 3, limit: 10 } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.equal(res.structuredContent.postings[0].id, "abc123"); assert.equal(res.structuredContent.postings[0].buyer, "GSA.PBS");
  assert.equal(res.structuredContent.total, 34);
  const q = client.log[0].url.searchParams;
  assert.equal(client.log[0].url.href.split("?")[0], "https://api.sam.gov/opportunities/v2/search");
  assert.equal(q.get("api_key"), "SAM-KEY-123456"); assert.equal(q.get("title"), "renovation");
  assert.equal(q.get("postedFrom"), mmddyyyy(364)); assert.equal(q.get("postedTo"), mmddyyyy(0));
  assert.equal(q.get("limit"), "10"); assert.equal(q.get("offset"), "2");
});

test("sam_gov: get_posting by noticeid (wire)", async () => {
  const client = await connect(() => json(200, { totalRecords: 1, opportunitiesData: [OPP] }));
  const res = await client.callTool({ name: "get_posting", arguments: { id: "abc123" } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.equal(res.structuredContent.deadline, "2026-10-04T15:00:00-05:00");
  assert.equal(client.log[0].url.searchParams.get("noticeid"), "abc123");
});

test("sam_gov: invalid key is an auth_error (wire)", async () => {
  const client = await connect(() => json(403, { error: { message: "An invalid api_key was supplied" } }));
  const res = await client.callTool({ name: "search_postings", arguments: {} });
  assert.equal(res.isError, true); assert.equal(res.structuredContent.error, "auth_error");
});
