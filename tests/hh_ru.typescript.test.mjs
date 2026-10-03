import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/jobs/hh_ru.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const dig = (o, p) => p.split(".").reduce((a, k) => (a == null ? a : a[k]), o);
process.env.PLATFORM_MCP_HH_RU_CLIENT_ID = "hh-cid";
process.env.PLATFORM_MCP_HH_RU_CLIENT_SECRET = "hh-SECRETvalue";
process.env.PLATFORM_MCP_HH_RU_USER_AGENT = "MyApp/1.0 (dev@example.com)";

async function connect(handler) {
  const tokens = [];
  globalThis.fetch = fakeFetch((url, init) => {
    if (url.href.split("?")[0] === "https://api.hh.ru/token") { tokens.push(init); return { body: {"access_token": "HH-APP-TOKEN", "token_type": "bearer"} }; }
    return handler(url, init);
  });
  const server = buildServer(SPEC);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  client.tokens = tokens;
  return client;
}

test("hh_ru: tools follow the vocabulary (wire)", async () => {
  const client = await connect(() => ({}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["get_posting", "me", "search"]);
  for (const t of tools) { assert.equal(t.inputSchema.additionalProperties, false); assert.ok(t.title); }
});

test("hh_ru: search maps documented fields (main, wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 200, body: {"items": [{"id": "93353083", "name": "Python developer", "employer": {"name": "Yandex"}, "area": {"name": "Москва"}, "alternate_url": "https://hh.ru/vacancy/93353083", "published_at": "2026-09-20T10:00:00+0300", "salary": {"from": 200000, "to": 300000, "currency": "RUR", "gross": false}, "snippet": {"responsibility": "Писать код"}}], "found": 1234, "page": 1, "pages": 124, "per_page": 10} }; });
  const res = await client.callTool({ name: "search", arguments: {"query": "python", "page": 2, "limit": 10} });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.deepEqual(dig(res.structuredContent, "postings.0.id"), "93353083");
  assert.deepEqual(dig(res.structuredContent, "postings.0.company"), "Yandex");
  assert.deepEqual(dig(res.structuredContent, "postings.0.salary_min"), 200000);
  assert.deepEqual(dig(res.structuredContent, "postings.0.currency"), "RUR");
  assert.deepEqual(dig(res.structuredContent, "total"), 1234);
  assert.deepEqual(dig(res.structuredContent, "next_page"), null);
  assert.equal(seen.url.href.split("?")[0], "https://api.hh.ru/vacancies");
  assert.equal(seen.init.method, "GET");
  assert.equal(seen.url.searchParams.get("text"), "python");
  assert.equal(seen.url.searchParams.get("page"), "1");
  assert.equal(seen.url.searchParams.get("per_page"), "10");
  assert.equal((seen.init.headers["Authorization"] ?? seen.init.headers["authorization"]), "Bearer HH-APP-TOKEN");
  assert.deepEqual(Object.fromEntries(new URLSearchParams(client.tokens.at(-1).body)), {"grant_type": "client_credentials", "client_id": "hh-cid", "client_secret": "hh-SECRETvalue"});
});

test("hh_ru: me maps documented fields (extra, wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 200, body: {"auth_type": "application"} }; });
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.deepEqual(dig(res.structuredContent, "ok"), true);
  assert.deepEqual(dig(res.structuredContent, "account.auth_type"), "application");
  assert.equal(seen.url.href.split("?")[0], "https://api.hh.ru/me");
  assert.equal(seen.init.method, "GET");

});

test("hh_ru: rate limit is an isError result (wire)", async () => {
  const client = await connect(() => ({ status: 429, headers: { "Retry-After": "30" } }));
  const res = await client.callTool({ name: "get_posting", arguments: {"id": "1"} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "rate_limited");
  assert.equal(res.structuredContent.retry_after_seconds, 30);
});
