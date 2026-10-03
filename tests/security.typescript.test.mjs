// Security review 2026-10 (docs/SECURITY_REVIEW_2026-10.md): the TypeScript runtime against the same cases as
// tests/test_security_python.py.
import assert from "node:assert/strict";
import { test } from "node:test";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, serverFactory, Transport, checkUrl, isPublicIp } from "../runtime/typescript/dist/index.js";
import { scrub } from "../runtime/typescript/dist/credentials.js";

const CASES = JSON.parse(fs.readFileSync(new URL("./fixtures/netguard_cases.json", import.meta.url), "utf8"));
const PUBLIC = "93.184.215.14";
const publicResolver = async () => [PUBLIC];
const hdrs = (map = {}) => ({ get: (k) => map[k.toLowerCase()] ?? null });
const jsonResp = (status, body, extra = {}) => ({ status, headers: hdrs({ "content-type": "application/json", ...extra }), text: async () => (body === undefined ? "" : JSON.stringify(body)) });
const textResp = (status, text, extra = {}) => ({ status, headers: hdrs(extra), text: async () => text, arrayBuffer: async () => new TextEncoder().encode(text).buffer });

async function client(spec, transport) {
  const server = buildServer(spec, transport);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const c = new Client({ name: "test", version: "0" });
  await c.connect(ct);
  return c;
}
async function clientOf(server) {
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const c = new Client({ name: "test", version: "0" });
  await c.connect(ct);
  return c;
}

// ---------------------------------------------------------------- SR-02: SSRF through multipart file: downloads
test("netguard: the shared IP table", () => {
  for (const [ip, pub] of Object.entries(CASES.ips)) assert.equal(isPublicIp(ip), pub, ip);
});

test("netguard: the shared URL cases", async () => {
  delete process.env.PLATFORM_MCP_ALLOW_PRIVATE_URLS;
  for (const c of CASES.urls) {
    let ok = true;
    try { await checkUrl(c.url, async () => [...c.resolves]); } catch (e) { assert.equal(e.kind, "invalid_input", String(e)); ok = false; }
    assert.equal(ok, c.ok, c.url);
  }
  process.env.PLATFORM_MCP_ALLOW_PRIVATE_URLS = "1";
  try { await checkUrl("http://169.254.169.254/", publicResolver); } finally { delete process.env.PLATFORM_MCP_ALLOW_PRIVATE_URLS; }
});

const MP_AUTH = { type: "bearer", field: "token", fields: [{ name: "token" }] };
const MP_SPEC = { id: "mpx", category: "builder_tools", label: "Mpx", docs_url: "https://docs.example/", verified_at: "2026-10-01",
  adapter: { base_url: "https://mp.example", rate_per_second: 50, auth: MP_AUTH,
    tools: { generate_image: { method: "POST", path: "/v2/generate", body_format: "multipart", body: { prompt: "prompt", image: "file:image_url" }, result: { fields: { job_id: "id", status: "status" } } } } } };

function mpClient(fetcher, resolver = publicResolver) {
  const t = new Transport("https://mp.example", MP_AUTH, { token: "TOKEN-mpx-123" }, 50, "test", fetcher);
  t.resolveHost = resolver;
  return client(MP_SPEC, t);
}

test("file downloads refuse metadata and private hosts", async () => {
  const log = [];
  const f = async (url, init) => { log.push({ url, init }); return url.endsWith("/v2/generate") ? jsonResp(200, { id: "j1", status: "queued" }) : textResp(200, "AKIA-SECRET"); };
  let c = await mpClient(f);
  let res = await c.callTool({ name: "generate_image", arguments: { prompt: "x", image_url: "http://169.254.169.254/latest/meta-data/iam/security-credentials/role" } });
  assert.equal(res.isError, true); assert.equal(res.structuredContent.error, "invalid_input");
  c = await mpClient(f, async () => ["10.0.0.7"]);
  res = await c.callTool({ name: "generate_image", arguments: { prompt: "x", image_url: "https://intranet.example/secret.png" } });
  assert.equal(res.isError, true);
  assert.equal(log.length, 0);
});

test("file downloads re-check every redirect and never follow one blindly", async () => {
  const log = [];
  const f = async (url, init) => {
    log.push({ url, init });
    if (url === "https://cdn.example/a.png") return textResp(302, "", { location: "http://127.0.0.1:8080/admin" });
    if (url === "https://cdn.example/b.png") return textResp(301, "", { location: "https://cdn2.example/b.png" });
    if (url === "https://cdn2.example/b.png") return textResp(200, "PNG", { "content-type": "image/png" });
    if (url.endsWith("/v2/generate")) return jsonResp(200, { id: "j1", status: "queued" });
    return textResp(200, "admin");
  };
  const c = await mpClient(f);
  let res = await c.callTool({ name: "generate_image", arguments: { prompt: "x", image_url: "https://cdn.example/a.png" } });
  assert.equal(res.isError, true);
  assert.deepEqual(log.map((l) => l.url), ["https://cdn.example/a.png"]);
  assert.equal(log[0].init.redirect, "manual");
  res = await c.callTool({ name: "generate_image", arguments: { prompt: "x", image_url: "https://cdn.example/b.png" } });
  assert.equal(res.isError, false);
  const gen = log.find((l) => l.url.endsWith("/v2/generate"));
  assert.equal(Buffer.from(await gen.init.body.get("image").arrayBuffer()).toString(), "PNG");
});

test("file downloads are capped at PLATFORM_MCP_MAX_DOWNLOAD_MB", async () => {
  process.env.PLATFORM_MCP_MAX_DOWNLOAD_MB = "0.001";
  try {
    const log = [];
    const f = async (url, init) => { log.push(url); return url.endsWith("/v2/generate") ? jsonResp(200, { id: "j1" }) : textResp(200, "x".repeat(5000)); };
    const res = await (await mpClient(f)).callTool({ name: "generate_image", arguments: { prompt: "x", image_url: "https://cdn.example/big.png" } });
    assert.equal(res.isError, true); assert.match(res.structuredContent.message, /larger/);
    assert.ok(!log.some((u) => u.endsWith("/v2/generate")));
  } finally { delete process.env.PLATFORM_MCP_MAX_DOWNLOAD_MB; }
});

// ---------------------------------------------------------------- SR-03: tool arguments spliced raw into the URL path
const PATH_AUTH = { type: "header", header: "X-Api-Key", field: "api_key", fields: [{ name: "api_key" }] };
const PATH_SPEC = { id: "pathy", category: "jobs", label: "Pathy", docs_url: "https://docs.example/", verified_at: "2026-10-01",
  adapter: { base_url: "https://api.pathy.example/v1", rate_per_second: 50, auth: PATH_AUTH, config_fields: [{ name: "org" }],
    tools: { get_posting: { path: "/jobs/{id}", result: { fields: { id: "id", title: "title" } } },
      search: { path: "/boards/{board}/jobs", path_params: { board: "fmt:{@org}/{query}" }, params: { page: "page" }, result: { items: "jobs", key: "postings", fields: { id: "id" } } } } } };

test("path arguments cannot add a query, a fragment or dot segments", async () => {
  const log = [];
  const f = async (url, init) => { log.push({ url, init }); return jsonResp(200, { id: "1", title: "t", jobs: [] }); };
  const c = await client(PATH_SPEC, new Transport(PATH_SPEC.adapter.base_url, PATH_AUTH, { api_key: "KEY-pathy-1", org: "acme" }, 50, "test", f));
  const cases = [["7?delete=true#x", "/v1/jobs/7%3Fdelete=true%23x"], ["a b", "/v1/jobs/a%20b"], ["100%", "/v1/jobs/100%25"],
    ["urn%3Ali%3Ashare%3A1", "/v1/jobs/urn%3Ali%3Ashare%3A1"], ["gb/00102498", "/v1/jobs/gb/00102498"],
    ["abc-1_2.3~:@!$&'()*+,;=", "/v1/jobs/abc-1_2.3~:@!$&'()*+,;="], ["café", "/v1/jobs/caf%C3%A9"], ["$&$`", "/v1/jobs/$&$%60"]];
  for (const [raw, want] of cases) {
    const res = await c.callTool({ name: "get_posting", arguments: { id: raw } });
    assert.equal(res.isError, false, raw);
    const u = log[log.length - 1].url;
    assert.equal(u, "https://api.pathy.example" + want, raw);
    assert.equal(new URL(u).pathname, want.replace("%25", "%25"), raw);
    assert.equal(new URL(u).search, "", raw);
  }
  const n = log.length;
  for (const raw of ["..", ".", "../../admin/users", "x/../../admin", "%2e%2E/admin", "a/.%2e/b"]) {
    const res = await c.callTool({ name: "get_posting", arguments: { id: raw } });
    assert.equal(res.isError, true, raw); assert.equal(res.structuredContent.error, "invalid_input", raw);
  }
  const res = await c.callTool({ name: "search", arguments: { query: "eng/../../x" } });
  assert.equal(res.isError, true); assert.equal(log.length, n);
  await c.callTool({ name: "search", arguments: { query: "eng" } });
  assert.equal(new URL(log[log.length - 1].url).pathname, "/v1/boards/acme/eng/jobs");
});

// ---------------------------------------------------------------- SR-04 / SR-05: redirects and the 401 re-login
for (const [extra, p, where] of [[{ token_param: "access_token" }, "/jobs/{id}", "query"], [{ header: "" }, "/t/{access_token}/jobs/{id}", "path"], [{}, "/jobs/{id}", "header"]]) {
  test(`401 retry carries the new token (${where})`, async () => {
    const auth = { type: "oauth2_client_credentials", token_url: "https://auth.tok.example/token", fields: [{ name: "client_id" }, { name: "client_secret" }], ...extra };
    const spec = { id: "tok", category: "jobs", label: "Tok", docs_url: "https://docs.example/", verified_at: "2026-10-01",
      adapter: { base_url: "https://api.tok.example", rate_per_second: 50, auth, tools: { get_posting: { path: p, result: { fields: { id: "id", title: "title" } } } } } };
    const minted = ["OLD-token-1", "NEW-token-2"]; const api = [];
    const f = async (url, init) => {
      if (url.startsWith("https://auth.tok.example/token")) return jsonResp(200, { access_token: minted.shift(), expires_in: 3600 });
      api.push({ url, init });
      return api.length === 1 ? jsonResp(401, { error: "expired" }) : jsonResp(200, { id: "9", title: "t" });
    };
    const c = await client(spec, new Transport(spec.adapter.base_url, auth, { client_id: "cid", client_secret: "csecret" }, 50, "test", f));
    const res = await c.callTool({ name: "get_posting", arguments: { id: "9" } });
    assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
    const retry = api[1]; const u = new URL(retry.url);
    const seen = { query: u.searchParams.get("access_token"), path: u.pathname, header: retry.init.headers.Authorization }[where];
    assert.ok(seen.includes("NEW-token-2"), seen);
    assert.ok(!(retry.url + (retry.init.headers.Authorization ?? "")).includes("OLD-token-1"));
    for (const a of api) assert.equal(a.init.redirect, "manual"); // an API redirect is never followed with the credentials attached
  });
}

// ---------------------------------------------------------------- SR-06: Streamable HTTP shares one transport
test("servers built by one HTTP factory share the minted token (no login per request)", async () => {
  const spec = { id: "httpx", category: "jobs", label: "H", docs_url: "https://docs.example/", verified_at: "2026-10-01",
    adapter: { base_url: "https://api.h.example", rate_per_second: 50,
      auth: { type: "oauth2_refresh_token", token_url: "https://auth.h.example/token", fields: [{ name: "client_id" }, { name: "refresh_token" }] },
      tools: { get_posting: { path: "/jobs/{id}", result: { fields: { id: "id" } } } } } };
  process.env.PLATFORM_MCP_HTTPX_CLIENT_ID = "cid"; process.env.PLATFORM_MCP_HTTPX_REFRESH_TOKEN = "R-1-single-use";
  try {
    const grants = [];
    const f = async (url, init) => {
      if (url.startsWith("https://auth.h.example/token")) {
        const rt = new URLSearchParams(init.body).get("refresh_token"); grants.push(rt);
        if (rt !== "R-1-single-use") return jsonResp(400, { error: "invalid_grant" });
        return jsonResp(200, { access_token: "A-1-abcdef", refresh_token: "R-2-rotated", expires_in: 3600 });
      }
      return jsonResp(200, { id: "1" });
    };
    const make = serverFactory(spec, f);
    for (let i = 0; i < 3; i++) {
      const res = await (await clientOf(make())).callTool({ name: "get_posting", arguments: { id: "1" } });
      assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
    }
    assert.deepEqual(grants, ["R-1-single-use"]);
  } finally { delete process.env.PLATFORM_MCP_HTTPX_CLIENT_ID; delete process.env.PLATFORM_MCP_HTTPX_REFRESH_TOKEN; }
});

// ---------------------------------------------------------------- SR-09: redaction of encoded secrets and auth schemes
test("Basic credentials and URL-encoded secrets are redacted", async () => {
  const auth = { type: "basic", username_field: "user", password_field: "password", fields: [{ name: "user" }, { name: "password" }] };
  const spec = { id: "basicx", category: "jobs", label: "B", docs_url: "https://docs.example/", verified_at: "2026-10-01",
    adapter: { base_url: "https://api.basic.example", rate_per_second: 50, auth, tools: { get_posting: { path: "/jobs/{id}", result: { fields: { id: "id" } } } } } };
  const b64 = Buffer.from("svc-user:p@ss w0rd/+").toString("base64");
  const echo = `bad request; you sent Authorization: Basic ${b64} and password=p%40ss%20w0rd%2F%2B (form: p%40ss+w0rd%2F%2B)`;
  const f = async () => textResp(500, echo);
  const c = await client(spec, new Transport("https://api.basic.example", auth, { user: "svc-user", password: "p@ss w0rd/+" }, 50, "test", f));
  const res = await c.callTool({ name: "get_posting", arguments: { id: "1" } });
  const msg = res.structuredContent.message;
  assert.equal(res.isError, true); assert.ok(!msg.includes(b64) && !msg.includes("p%40ss") && !msg.includes("w0rd"), msg);
  assert.equal(scrub("Authorization: Bearer abcdefghijkl123"), "Authorization: Bearer <redacted>");
  assert.equal(scrub('{"authorization": "Basic Zm9vOmJhcg=="}'), '{"authorization": <redacted>}');
});

// ---------------------------------------------------------------- SR-10: rotated refresh-token state file
test("the state file is private and a planted temp-file symlink is never followed", async () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "secreview-"));
  const state = path.join(tmp, "state"); fs.mkdirSync(state, { mode: 0o755 });
  const victim = path.join(tmp, "victim.txt"); fs.writeFileSync(victim, "keep");
  fs.symlinkSync(victim, path.join(state, "rot.tmp")); fs.symlinkSync(victim, path.join(state, "rot.json.tmp"));
  fs.writeFileSync(path.join(state, "rot.json"), JSON.stringify({ refresh_token: "R-old-123456" })); fs.chmodSync(path.join(state, "rot.json"), 0o644);
  process.env.PLATFORM_MCP_STATE_DIR = state;
  try {
    const auth = { type: "oauth2_refresh_token", token_url: "https://auth.rot.example/token", state_key: "rot", fields: [{ name: "client_id" }, { name: "refresh_token" }] };
    const spec = { id: "rot", category: "jobs", label: "R", docs_url: "https://docs.example/", verified_at: "2026-10-01",
      adapter: { base_url: "https://api.rot.example", rate_per_second: 50, auth, tools: { get_posting: { path: "/jobs/{id}", result: { fields: { id: "id" } } } } } };
    const f = async (url) => url.startsWith("https://auth.rot.example") ? jsonResp(200, { access_token: "A-123456", refresh_token: "R-new-654321", expires_in: 3600 }) : jsonResp(200, { id: "1" });
    const c = await client(spec, new Transport("https://api.rot.example", auth, { client_id: "c", refresh_token: "R-env-000000" }, 50, "test", f));
    assert.equal((await c.callTool({ name: "get_posting", arguments: { id: "1" } })).isError, false);
    assert.equal(fs.readFileSync(victim, "utf8"), "keep");
    assert.deepEqual(JSON.parse(fs.readFileSync(path.join(state, "rot.json"), "utf8")), { refresh_token: "R-new-654321" });
    assert.equal(fs.statSync(path.join(state, "rot.json")).mode & 0o777, 0o600);
    const fresh = path.join(tmp, "fresh", "nested"); process.env.PLATFORM_MCP_STATE_DIR = fresh;
    const t2 = new Transport("https://api.rot.example", auth, { client_id: "c", refresh_token: "R-env-000000" }, 50, "test", f);
    t2.storeRotatedRefreshToken("R-third-999999");
    assert.equal(fs.statSync(fresh).mode & 0o777, 0o700); assert.equal(fs.statSync(path.join(fresh, "rot.json")).mode & 0o777, 0o600);
  } finally { delete process.env.PLATFORM_MCP_STATE_DIR; }
});

// ---------------------------------------------------------------- SR-11: a cursor that does not advance ends the walk
test("a repeated cursor is not offered again", async () => {
  const spec = { id: "cur", category: "jobs", label: "C", docs_url: "https://docs.example/", verified_at: "2026-10-01",
    adapter: { base_url: "https://api.cur.example", rate_per_second: 50, auth: { type: "none" },
      tools: { search: { path: "/jobs", params: { after: "cursor", n: "limit" }, result: { items: "jobs", key: "postings", next_cursor: "next", fields: { id: "id" } } } } } };
  const f = async () => jsonResp(200, { jobs: [{ id: 1 }], next: "C2" });
  const c = await client(spec, new Transport("https://api.cur.example", { type: "none" }, {}, 50, "test", f));
  assert.equal((await c.callTool({ name: "search", arguments: { query: "x", limit: 1 } })).structuredContent.next_cursor, "C2");
  const again = (await c.callTool({ name: "search", arguments: { query: "x", limit: 1, cursor: "C2" } })).structuredContent;
  assert.equal(again.next_cursor, null); assert.equal(again.next_page, null);
});

// ---------------------------------------------------------------- SR-16: the rate limit holds under concurrent calls
test("concurrent requests respect rate_per_second", async () => {
  const times = [];
  const f = async () => { times.push(Date.now()); return jsonResp(200, { id: "1" }); };
  const spec = { id: "rl", category: "jobs", label: "R", docs_url: "https://docs.example/", verified_at: "2026-10-01",
    adapter: { base_url: "https://api.rl.example", rate_per_second: 10, auth: { type: "none" }, tools: { get_posting: { path: "/jobs/{id}", result: { fields: { id: "id" } } } } } };
  const c = await client(spec, new Transport("https://api.rl.example", { type: "none" }, {}, 10, "test", f));
  const t0 = Date.now();
  await Promise.all(Array.from({ length: 20 }, (_, i) => c.callTool({ name: "get_posting", arguments: { id: String(i) } })));
  // a burst of 10 (one second's worth), then one every 100 ms: the 20th request cannot start before ~1000 ms
  assert.ok(Math.max(...times) - t0 >= 850, `20 requests at 10/s were all sent within ${Math.max(...times) - t0} ms`);
});
