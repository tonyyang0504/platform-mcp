// Twin of tests/test_environments_python.py: environment selection, override validation, OAuth2 token URL
// switching, per-environment refresh-token state and redaction, over tests/fixtures/environments_cases.json.
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, selectEnvironment, stateKey, validHttpsUrl } from "../runtime/typescript/dist/index.js";
import { scrub } from "../runtime/typescript/dist/credentials.js";

const CASES = JSON.parse(fs.readFileSync(new URL("./fixtures/environments_cases.json", import.meta.url), "utf8"));
const CREDS = { CLIENT_ID: "cid-0123456789", CLIENT_SECRET: "csecret-0123456789", REFRESH_TOKEN: "rt-0123456789abcdef" };
const spec = () => ({ id: "shop", category: "ecommerce_channels", docs_url: "https://docs.shop.example", adapter: structuredClone(CASES.adapter) });
const envOf = (e) => Object.fromEntries(Object.entries(e).map(([k, v]) => [`PLATFORM_MCP_SHOP_${k}`, v]));

function withEnv(vars, fn) {
  const saved = {};
  for (const k of Object.keys(process.env)) if (k.startsWith("PLATFORM_MCP_")) { saved[k] = process.env[k]; delete process.env[k]; }
  Object.assign(process.env, vars);
  const restore = () => { for (const k of Object.keys(process.env)) if (k.startsWith("PLATFORM_MCP_")) delete process.env[k]; Object.assign(process.env, saved); };
  return Promise.resolve().then(fn).finally(restore);
}

const reply = (status, body) => ({
  status,
  headers: { get: (k) => (k.toLowerCase() === "content-type" ? (typeof body === "string" ? "text/plain" : "application/json") : null) },
  text: async () => (typeof body === "string" ? body : JSON.stringify(body)),
});

async function connect(handler) {
  const log = [];
  const fetcher = async (url, init) => { const u = new URL(url); log.push({ url: u, init }); return handler(u, init, log.length); };
  const server = buildServer(spec(), undefined, fetcher);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return { client, log };
}

test("environment selection (same cases as the Python twin)", () => {
  for (const c of CASES.select) {
    const adapter = spec().adapter;
    if (c.error) {
      assert.throws(() => selectEnvironment("shop", adapter, envOf(c.env)), (e) => e.kind === "invalid_input" && e.message === c.error, JSON.stringify(c.env));
      continue;
    }
    const { adapter: eff, environment } = selectEnvironment("shop", adapter, envOf(c.env));
    const label = JSON.stringify(c.env);
    assert.equal(environment, c.environment, label);
    assert.equal(eff.base_url, c.base_url, label);
    assert.equal(eff.auth.token_url, c.token_url, label);
    assert.equal(eff.auth.scope, c.scope, label);
    assert.equal(eff.tools.me.path, c.me_path, label);
    assert.equal(eff.tools.list_orders.path, "/orders", label);
    assert.deepEqual(eff.headers, c.headers, label);
    if (c.auth_url) assert.equal(eff.auth.auth_url, c.auth_url, label);
    assert.equal(eff.environments, undefined, label);
    assert.deepEqual(adapter, spec().adapter, "the catalog spec is never mutated");
  }
});

test("base URL override validation never echoes the value", () => {
  for (const [value, valid, why] of CASES.overrides) {
    assert.equal(validHttpsUrl(value), valid, value);
    const env = { PLATFORM_MCP_SHOP_BASE_URL: value };
    if (valid) {
      const { adapter, environment } = selectEnvironment("shop", spec().adapter, env);
      assert.equal(adapter.base_url, value);
      assert.equal(environment, "production+base_url");
      continue;
    }
    assert.throws(() => selectEnvironment("shop", spec().adapter, env), (e) => {
      assert.equal(e.kind, "invalid_input");
      assert.equal(e.message, `configuration: PLATFORM_MCP_SHOP_BASE_URL is not a valid override: ${why}`);
      assert.ok(value === "https://" || !e.message.includes(value), value);
      assert.ok(!e.message.includes("hunter2secret") && !e.message.includes("abcdef123456"));
      return true;
    });
  }
});

test("state key is per environment", () => {
  assert.equal(stateKey("shop", "production"), "shop");
  assert.equal(stateKey("shop", "production+base_url"), "shop");
  assert.equal(stateKey("shop", "sandbox"), "shop.sandbox");
  assert.equal(stateKey("shop", "sandbox+base_url"), "shop.sandbox");
});

for (const [env, tokenHost, apiBase, reportsHost, scope] of [
  [{}, "auth.shop.example", "https://api.shop.example/v1", "reports.shop.example", "prod.scope"],
  [{ ENV: "sandbox" }, "api.sandbox.shop.example", "https://api.sandbox.shop.example/v1", "reports.sandbox.shop.example", "sandbox.scope"],
  [{ ENV: "dynamic" }, "auth.sandbox.shop.example", "https://api.sandbox.shop.example/v1", "reports.shop.example", "prod.scope"],
]) {
  test(`OAuth2 token URL and hosts switch with the environment ${JSON.stringify(env)}`, () => withEnv(envOf({ ...CREDS, ...env }), async () => {
    const { client, log } = await connect((u) => {
      if (u.pathname === "/oauth/token") return reply(200, { access_token: `at-${u.host}`, expires_in: 3600 });
      if (u.pathname.endsWith("/orders")) return reply(200, { orders: [{ id: "o-1" }] });
      if (u.pathname === "/me") return reply(200, { id: "me-1", name: "Shop" });
      return reply(404, "no route");
    });
    const r = await client.callTool({ name: "list_orders", arguments: {} });
    assert.equal(r.isError, false, JSON.stringify(r.structuredContent));
    assert.equal(r.structuredContent.orders[0].id, "o-1");
    const r2 = await client.callTool({ name: "me", arguments: {} });
    assert.equal(r2.isError, false, JSON.stringify(r2.structuredContent));
    const tokens = log.filter((x) => x.url.pathname === "/oauth/token");
    assert.equal(tokens.length, 1);
    assert.equal(tokens[0].url.host, tokenHost);
    const form = new URLSearchParams(String(tokens[0].init.body));
    assert.equal(form.get("grant_type"), "refresh_token");
    assert.equal(form.get("scope"), scope);
    const api = log.find((x) => x.url.pathname.endsWith("/orders"));
    assert.equal(api.url.href, `${apiBase}/orders`);
    const h = Object.fromEntries(Object.entries(api.init.headers).map(([k, v]) => [k.toLowerCase(), v]));
    assert.equal(h.authorization, `Bearer at-${tokenHost}`);
    assert.equal(h["x-api-version"], "3");
    assert.equal(h["x-sandbox"], env.ENV === "dynamic" ? "v2" : undefined);
    assert.equal(log.find((x) => x.url.pathname === "/me").url.host, reportsHost);
  }));
}

test("a bad environment is a clean tool error and sends nothing", () => withEnv(envOf({ ...CREDS, ENV: "staging" }), async () => {
  const { client, log } = await connect(() => reply(200, {}));
  const r = await client.callTool({ name: "list_orders", arguments: {} });
  assert.equal(r.isError, true);
  assert.deepEqual(r.structuredContent, { error: "invalid_input", message: CASES.select.at(-2).error });
  assert.equal(log.length, 0);
}));

test("an invalid override is a tool error that never echoes the value", () => withEnv(envOf({ ...CREDS, BASE_URL: "https://svc-user:p4ssw0rd-9f8e7d@gateway.corp.example/api" }), async () => {
  const { client } = await connect(() => reply(200, {}));
  const r = await client.callTool({ name: "list_orders", arguments: {} });
  assert.equal(r.isError, true);
  assert.equal(r.structuredContent.error, "invalid_input");
  const text = JSON.stringify(r.structuredContent);
  for (const s of ["p4ssw0rd", "gateway.corp.example", "svc-user"]) assert.ok(!text.includes(s), s);
  assert.ok(text.includes("PLATFORM_MCP_SHOP_BASE_URL"));
}));

test("the override host is redacted from upstream and network errors", () => {
  const priv = "https://gw-7f3a.internal.corp.example/shop-proxy";
  return withEnv(envOf({ ...CREDS, BASE_URL: priv, ENV: "sandbox" }), async () => {
    let fail = "http";
    const { client, log } = await connect((u) => {
      if (u.pathname === "/oauth/token") return reply(200, { access_token: "at-sandbox-777777", expires_in: 3600 });
      if (fail === "net") throw new TypeError(`fetch failed: cannot connect to ${priv}/orders`);
      return reply(502, `upstream ${priv}/orders failed; token at-sandbox-777777`);
    });
    const r = await client.callTool({ name: "list_orders", arguments: {} });
    assert.equal(r.isError, true);
    assert.equal(r.structuredContent.error, "upstream_error");
    const msg = r.structuredContent.message;
    assert.ok(!msg.includes(priv) && !msg.includes("at-sandbox-777777") && msg.includes("<redacted>"), msg);
    assert.equal(log.find((x) => x.url.pathname.endsWith("/orders")).url.href, `${priv}/orders`);
    assert.equal(log.find((x) => x.url.pathname === "/oauth/token").url.host, "api.sandbox.shop.example");
    fail = "net";
    const r2 = await client.callTool({ name: "list_orders", arguments: {} });
    assert.equal(r2.isError, true);
    assert.ok(!JSON.stringify(r2.structuredContent).includes(priv));
    assert.ok(!scrub(`GET ${priv}/orders`).includes(priv));
  });
});

test("rotated refresh tokens are saved per environment", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "pmc-env-"));
  return withEnv({ ...envOf({ ...CREDS, ENV: "sandbox" }), PLATFORM_MCP_STATE_DIR: dir }, async () => {
    const { client } = await connect((u) => u.pathname === "/oauth/token"
      ? reply(200, { access_token: "at-sb-000000", refresh_token: "rt-rotated-sandbox-1", expires_in: 3600 })
      : reply(200, { orders: [] }));
    const r = await client.callTool({ name: "list_orders", arguments: {} });
    assert.equal(r.isError, false, JSON.stringify(r.structuredContent));
    assert.ok(fs.existsSync(path.join(dir, "shop.sandbox.json")));
    assert.ok(!fs.existsSync(path.join(dir, "shop.json")), "a sandbox token never replaces the production one");
  });
});
