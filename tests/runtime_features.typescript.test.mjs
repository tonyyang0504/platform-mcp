import assert from "node:assert/strict";
import { test } from "node:test";
import fs from "node:fs";
import crypto from "node:crypto";
import os from "node:os";
import path from "node:path";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = { id: "sess", category: "social", label: "Sess", docs_url: "https://docs.example/", verified_at: "2026-09-24",
  adapter: { base_url: "https://api.example", rate_per_second: 50,
    auth: { type: "session", login: { method: "POST", path: "/login", body: { identifier: "@identifier", password: "@password" } }, token_path: "accessJwt", token_ttl_seconds: 600, fields: [{ name: "identifier" }, { name: "password" }] },
    tools: { me: { kind: "probe", path: "/me" }, publish_text: { method: "POST", path: "/post", body: { "record.text": "text", "record.createdAt": "now", collection: "=app.bsky.feed.post" }, result: { fields: { id: "uri" } } } } } };

const fakeFetch = (log) => async (url, init) => {
  log.push({ url, init });
  if (url.endsWith("/login")) return { status: 200, headers: { get: () => "application/json" }, text: async () => JSON.stringify({ accessJwt: log.filter((l) => l.url.endsWith("/login")).length === 1 ? "T1" : "T2" }) };
  if (url.endsWith("/me")) { const first = log.filter((l) => l.url.endsWith("/me")).length === 1; return { status: first ? 401 : 200, headers: { get: () => "application/json" }, text: async () => JSON.stringify({ handle: "x" }) }; }
  return { status: 200, headers: { get: () => "application/json" }, text: async () => JSON.stringify({ uri: "at://did/app.bsky.feed.post/1" }) };
};

async function connect(log) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { identifier: "u", password: "p" }, 50, "test", fakeFetch(log)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("session login, bearer, re-login on 401 (wire)", async () => {
  const log = [];
  const client = await connect(log);
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, false);
  const logins = log.filter((l) => l.url.endsWith("/login"));
  assert.equal(logins.length, 2);
  assert.equal(log[log.length - 1].init.headers.Authorization, "Bearer T2");
  assert.deepEqual(JSON.parse(logins[0].init.body), { identifier: "u", password: "p" });
});

test("nested body keys, literals and now (wire)", async () => {
  const log = [];
  const client = await connect(log);
  const res = await client.callTool({ name: "publish_text", arguments: { text: "hello" } });
  assert.equal(res.isError, false);
  const body = JSON.parse(log[log.length - 1].init.body);
  assert.equal(body.record.text, "hello");
  assert.equal(body.collection, "app.bsky.feed.post");
  assert.match(body.record.createdAt, /^\d{4}-\d{2}-\d{2}T/);
});


const TYPED_SPEC = { id: "typed", category: "ecommerce_channels", label: "Typed", docs_url: "https://docs.example/", verified_at: "2026-09-24",
  adapter: { base_url: "https://api.example", rate_per_second: 50, auth: { type: "bearer", field: "token", fields: [{ name: "token" }] },
    tools: {
      set_inventory: { method: "PUT", path: "/products/{listing_id}", body: { manage_stock: "json:true", stock_quantity: "quantity", regular_price: "str:quantity", weight: "json:0" }, result: { fields: { listing_id: "id" } } },
      end_listing: { method: "DELETE", path: "/products/{listing_id}", result: { fields: { listing_id: "=gone", status: "=ended" } } } } } };

test("typed literals, string coercion and empty 204 bodies (wire)", async () => {
  const log = [];
  const fetcher = async (url, init) => { log.push({ url, init }); return init.method === "DELETE" ? { status: 204, headers: { get: () => null }, text: async () => "" } : { status: 200, headers: { get: () => "application/json" }, text: async () => JSON.stringify({ id: 9 }) }; };
  const server = buildServer(TYPED_SPEC, new Transport(TYPED_SPEC.adapter.base_url, TYPED_SPEC.adapter.auth, { token: "t" }, 50, "test", fetcher));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  const res = await client.callTool({ name: "set_inventory", arguments: { listing_id: "9", quantity: 3 } });
  assert.equal(res.isError, false);
  assert.deepEqual(JSON.parse(log[0].init.body), { manage_stock: true, stock_quantity: 3, regular_price: "3", weight: 0 });
  const gone = await client.callTool({ name: "end_listing", arguments: { listing_id: "9" } });
  assert.equal(gone.isError, false);
  assert.equal(gone.structuredContent.status, "ended");
});


test("require drops feed rows without the listed fields (wire)", async () => {
  const spec = { id: "feed", category: "jobs", label: "Feed", docs_url: "https://docs.example/", verified_at: "2026-09-24",
    adapter: { base_url: "https://feed.example", rate_per_second: 50, auth: { type: "none", fields: [] },
      tools: { search: { path: "/api", result: { items: "$", key: "postings", require: ["id"], fields: { id: "id", title: "position" } } } } } };
  const fetcher = async () => ({ status: 200, headers: { get: () => "application/json" }, text: async () => JSON.stringify([{ legal: "terms" }, { id: 1, position: "Dev" }, { id: null, position: "x" }]) });
  const server = buildServer(spec, new Transport(spec.adapter.base_url, spec.adapter.auth, {}, 50, "test", fetcher));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  const res = await client.callTool({ name: "search", arguments: { query: "dev" } });
  assert.equal(res.isError, false);
  assert.deepEqual(res.structuredContent.postings.map((p) => p.id), ["1"]);
});


test("fixed headers and uuid expression (wire)", async () => {
  const spec = { id: "mx", category: "messaging", label: "Mx", docs_url: "https://docs.example/", verified_at: "2026-09-24",
    adapter: { base_url: "https://mx.example", rate_per_second: 50, auth: { type: "bearer", field: "token", fields: [{ name: "token" }] }, headers: { "X-Crisp-Tier": "plugin" },
      tools: { send: { method: "PUT", path: "/rooms/{to}/send/m.room.message/{txn}", path_params: { txn: "uuid" }, body: { msgtype: "=m.text", body: "text" }, result: { fields: { message_id: "event_id", status: "=sent" } } } } } };
  const log = [];
  const fetcher = async (url, init) => { log.push({ url, init }); return { status: 200, headers: { get: () => "application/json" }, text: async () => JSON.stringify({ event_id: "$e1" }) }; };
  process.env.PLATFORM_MCP_MX_TOKEN = "t";
  const server = buildServer(spec, undefined, fetcher); // credentials resolve lazily on the first call
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  const r1 = await client.callTool({ name: "send", arguments: { to: "r1", text: "hi" } });
  await client.callTool({ name: "send", arguments: { to: "r1", text: "hi" } });
  delete process.env.PLATFORM_MCP_MX_TOKEN;
  assert.equal(r1.isError, false);
  assert.equal(log[0].init.headers["X-Crisp-Tier"], "plugin");
  assert.equal(log[0].init.headers.Authorization, "Bearer t");
  assert.match(log[0].url, /\/rooms\/r1\/send\/m\.room\.message\/[0-9a-f-]{36}$/);
  assert.notEqual(log[0].url, log[1].url);
});


test("digit segments in body keys build arrays (wire)", async () => {
  const spec = { id: "sg", category: "messaging", label: "Sg", docs_url: "https://docs.example/", verified_at: "2026-09-24",
    adapter: { base_url: "https://sg.example", rate_per_second: 50, auth: { type: "bearer", field: "api_key", fields: [{ name: "api_key" }] },
      tools: { send: { method: "POST", path: "/v3/mail/send", body: { "personalizations.0.to.0.email": "to", "from.email": "@sender", subject: "subject", "content.0.type": "=text/plain", "content.0.value": "text" }, result: { fields: { status: "=queued" } } } } } };
  const log = [];
  const fetcher = async (url, init) => { log.push({ url, init }); return { status: 202, headers: { get: () => null }, text: async () => "" }; };
  const server = buildServer(spec, new Transport(spec.adapter.base_url, spec.adapter.auth, { api_key: "k", sender: "me@x" }, 50, "test", fetcher));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  const res = await client.callTool({ name: "send", arguments: { to: "a@b", subject: "s", text: "hi" } });
  assert.equal(res.isError, false);
  assert.deepEqual(JSON.parse(log[0].init.body), { personalizations: [{ to: [{ email: "a@b" }] }], from: { email: "me@x" }, subject: "s", content: [{ type: "text/plain", value: "hi" }] });
});


test("escaped dots in body keys (wire)", async () => {
  const spec = { id: "mx2", category: "messaging", label: "Mx2", docs_url: "https://docs.example/", verified_at: "2026-09-24",
    adapter: { base_url: "https://mx.example", rate_per_second: 50, auth: { type: "none", fields: [] },
      tools: { reply: { method: "PUT", path: "/rooms/{channel}/send/m.room.message/{txn}", path_params: { txn: "uuid" }, body: { msgtype: "=m.text", body: "text", "m\\.relates_to.rel_type": "=m.thread", "m\\.relates_to.event_id": "thread_id", "m\\.relates_to.m\\.in_reply_to.event_id": "thread_id" }, result: { fields: { message_id: "event_id", status: "=sent" } } } } } };
  const log = [];
  const fetcher = async (url, init) => { log.push({ url, init }); return { status: 200, headers: { get: () => "application/json" }, text: async () => JSON.stringify({ event_id: "$e2" }) }; };
  const server = buildServer(spec, new Transport(spec.adapter.base_url, spec.adapter.auth, {}, 50, "test", fetcher));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  const res = await client.callTool({ name: "reply", arguments: { channel: "r1", thread_id: "$t", text: "yo" } });
  assert.equal(res.isError, false);
  assert.deepEqual(JSON.parse(log[0].init.body), { msgtype: "m.text", body: "yo", "m.relates_to": { rel_type: "m.thread", event_id: "$t", "m.in_reply_to": { event_id: "$t" } } });
});


test("array element, int coercion and per-instance session login (wire)", async () => {
  const spec = { id: "lem", category: "social", label: "Lem", docs_url: "https://docs.example/", verified_at: "2026-09-24",
    adapter: { base_url: "https://{instance}", rate_per_second: 50,
      auth: { type: "session", login: { method: "POST", path: "/api/v3/user/login", body: { username_or_email: "@user", password: "@password" } }, token_path: "jwt", token_ttl_seconds: 600, fields: [{ name: "user" }, { name: "password" }] },
      config_fields: [{ name: "instance", required: true }, { name: "community_id", required: true }],
      tools: { publish_image: { method: "POST", path: "/api/v3/post", body: { community_id: "int:@community_id", name: "text", url: "image_urls.0" }, result: { root: "post_view.post", fields: { id: "id" } } } } } };
  const log = [];
  const fetcher = async (url, init) => { log.push({ url, init }); return url.endsWith("/login") ? { status: 200, headers: { get: () => "application/json" }, text: async () => JSON.stringify({ jwt: "J" }) } : { status: 200, headers: { get: () => "application/json" }, text: async () => JSON.stringify({ post_view: { post: { id: 42 } } }) }; };
  const server = buildServer(spec, new Transport(spec.adapter.base_url, spec.adapter.auth, { user: "u", password: "p", instance: "lemmy.example", community_id: "7" }, 50, "test", fetcher));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  const res = await client.callTool({ name: "publish_image", arguments: { text: "hi", image_urls: ["https://i/1.png", "https://i/2.png"] } });
  assert.equal(res.isError, false);
  assert.equal(log[0].url, "https://lemmy.example/api/v3/user/login");
  assert.equal(log[1].init.headers.Authorization, "Bearer J");
  assert.deepEqual(JSON.parse(log[1].init.body), { community_id: 7, name: "hi", url: "https://i/1.png" });
});


test("oauth2 refresh-token grant with body client auth and extra headers (wire)", async () => {
  const spec = { id: "ets", category: "ecommerce_channels", label: "Ets", docs_url: "https://docs.example/", verified_at: "2026-09-24",
    adapter: { base_url: "https://api.ets.example/v3", rate_per_second: 50,
      auth: { type: "oauth2_refresh_token", token_url: "https://api.ets.example/v3/public/oauth/token", client_auth: "body", extra_headers: { "x-api-key": "client_id" }, fields: [{ name: "client_id" }, { name: "refresh_token" }] },
      tools: { me: { kind: "probe", path: "/application/users/me" } } } };
  const log = []; let tokens = 0, calls = 0;
  const fetcher = async (url, init) => {
    log.push({ url, init });
    if (url.endsWith("/oauth/token")) return { status: 200, headers: { get: () => "application/json" }, text: async () => JSON.stringify({ access_token: `A${++tokens}`, expires_in: 3600 }) };
    calls += 1;
    return { status: calls === 2 ? 401 : 200, headers: { get: () => "application/json" }, text: async () => JSON.stringify({ user_id: 1 }) };
  };
  const server = buildServer(spec, new Transport(spec.adapter.base_url, spec.adapter.auth, { client_id: "cid", refresh_token: "R" }, 50, "test", fetcher));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  const first = await client.callTool({ name: "me", arguments: {} });
  assert.equal(first.isError, false);
  assert.equal(log[0].init.body, "grant_type=refresh_token&refresh_token=R&client_id=cid");
  assert.equal(log[0].init.headers.Authorization, undefined);
  assert.equal(log[1].init.headers.Authorization, "Bearer A1");
  assert.equal(log[1].init.headers["x-api-key"], "cid");
  const second = await client.callTool({ name: "me", arguments: {} });
  assert.equal(second.isError, false);
  assert.equal(tokens, 2);
  assert.equal(log[log.length - 1].init.headers.Authorization, "Bearer A2");
});


const ROT = { id: "rot", category: "ecommerce_channels", label: "Rot", docs_url: "https://docs.example/", verified_at: "2026-09-24",
  adapter: { base_url: "https://api.rot.example", rate_per_second: 50, headers: { "Content-Type": "application/vnd.rot.v1+json" },
    auth: { type: "oauth2_refresh_token", token_url: "https://api.rot.example/token", client_auth: "body", fields: [{ name: "client_id" }, { name: "client_secret" }, { name: "refresh_token" }] },
    tools: { me: { kind: "probe", path: "/me" },
      update_listing: { method: "PUT", path: "/offers/{listing_id}", body: { price: "str:price" }, result: { fields: { listing_id: "id" } } },
      create_listing: { method: "POST", path: "/listings", body_format: "form", body: { title: "title", quantity: "int:quantity", is_supply: "json:false" }, result: { fields: { listing_id: "listing_id" } } } } } };

async function rotClient(fetcher, creds, auth = ROT.adapter.auth) {
  const t = new Transport(ROT.adapter.base_url, auth, creds, 50, "test", fetcher);
  t.fixedHeaders = ROT.adapter.headers;
  const server = buildServer(ROT, t);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}
const jsonResp = (status, body) => ({ status, headers: { get: () => "application/json" }, text: async () => (body === undefined ? "" : JSON.stringify(body)) });

test("rotating refresh tokens are reused and persisted 0600 (wire)", async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "pmcp-"));
  process.env.PLATFORM_MCP_STATE_DIR = dir;
  const log = []; let n = 0, me = 0;
  const fetcher = async (url, init) => {
    log.push({ url, init });
    if (url.endsWith("/token")) { n += 1; return jsonResp(200, { access_token: `ACCESS-${n}`, refresh_token: `REFRESH-${n + 1}`, expires_in: 3600 }); }
    me += 1; return jsonResp(me === 2 ? 401 : 200, { id: 1 });
  };
  const auth = { ...ROT.adapter.auth, state_key: "rot" };
  const client = await rotClient(fetcher, { client_id: "cid", client_secret: "SECRET-XYZ", refresh_token: "REFRESH-1" }, auth);
  await client.callTool({ name: "me", arguments: {} });
  await client.callTool({ name: "me", arguments: {} });
  const forms = log.filter((l) => l.url.endsWith("/token")).map((l) => new URLSearchParams(l.init.body));
  assert.equal(forms[0].get("refresh_token"), "REFRESH-1");
  assert.equal(forms[1].get("refresh_token"), "REFRESH-2");
  const file = path.join(dir, "rot.json");
  assert.equal(JSON.parse(fs.readFileSync(file, "utf8")).refresh_token, "REFRESH-3");
  assert.equal(fs.statSync(file).mode & 0o777, 0o600);
  const fresh = new Transport(ROT.adapter.base_url, auth, { client_id: "cid", client_secret: "s", refresh_token: "STALE" }, 50, "test", fetcher);
  assert.equal(fresh.creds.refresh_token, "REFRESH-3");
  delete process.env.PLATFORM_MCP_STATE_DIR;
});

test("error bodies never echo known secrets (wire)", async () => {
  const fetcher = async () => jsonResp(400, { error: "invalid_grant", refresh_token: "REFRESH-ONE", hint: "client SECRET-XYZ rejected" });
  const client = await rotClient(fetcher, { client_id: "cid", client_secret: "SECRET-XYZ", refresh_token: "REFRESH-ONE" });
  const res = await client.callTool({ name: "me", arguments: {} });
  const text = res.content[0].text;
  assert.equal(res.isError, true);
  assert.ok(!text.includes("REFRESH-ONE") && !text.includes("SECRET-XYZ") && text.includes("<redacted>"), text);
});

test("form bodies and a pinned vendor content type (wire)", async () => {
  const log = [];
  const fetcher = async (url, init) => { log.push({ url, init }); return url.endsWith("/token") ? jsonResp(200, { access_token: "ACCESS-ONE", expires_in: 3600 }) : jsonResp(200, url.includes("/offers/") ? { id: 9 } : { listing_id: 5 }); };
  const client = await rotClient(fetcher, { client_id: "cid", client_secret: "SECRET-XYZ", refresh_token: "REFRESH-ONE" });
  assert.equal((await client.callTool({ name: "create_listing", arguments: { title: "Mug", price: 9.5, quantity: 3 } })).isError, false);
  const create = log.find((l) => l.url.endsWith("/listings"));
  assert.deepEqual(Object.fromEntries(new URLSearchParams(create.init.body)), { title: "Mug", quantity: "3", is_supply: "false" });
  assert.equal((await client.callTool({ name: "update_listing", arguments: { listing_id: "9", price: 12 } })).isError, false);
  const put = log.find((l) => l.url.includes("/offers/9"));
  assert.equal(put.init.headers["Content-Type"], "application/vnd.rot.v1+json");
});


const ADS = { id: "adz", category: "ads", label: "Adz", docs_url: "https://docs.example/", verified_at: "2026-09-24",
  adapter: { base_url: "https://api.adz.example", rate_per_second: 50, auth: { type: "bearer", field: "token", fields: [{ name: "token" }] },
    tools: {
      pause_resume: { method: "POST", path: "/campaigns/{campaign_id}", headers: { "X-RestLi-Method": "PARTIAL_UPDATE" }, body: { status: "map:action:pause=PAUSED,resume=ACTIVE" }, result: { fields: { campaign_id: "=ok", status: "=updated" } } },
      list_campaigns: { path: "/adCampaigns?q=search", query_safe: "(),:", params: { search: "=(status:(values:List(ACTIVE)))", count: "limit" }, result: { items: "elements", key: "campaigns", fields: { id: "id", name: "name" } } },
      update_budget: { method: "PATCH", path: "/ad_accounts/{ad_account}/campaigns", path_params: { ad_account: "@ad_account" }, body: { "0.id": "campaign_id", "0.daily_spend_cap": "int:daily_budget" }, result: { fields: { campaign_id: "=ok", status: "=updated" } } } } } };

test("enum map, per-tool headers, literal Rest.li query, array bodies, strict integers (wire)", async () => {
  const log = [];
  const fetcher = async (url, init) => { log.push({ url, init }); return url.includes("adCampaigns") ? jsonResp(200, { elements: [{ id: 1, name: "A" }] }) : jsonResp(200, {}); };
  const server = buildServer(ADS, new Transport(ADS.adapter.base_url, ADS.adapter.auth, { token: "TOKEN-123", ad_account: "9" }, 50, "test", fetcher));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  assert.equal((await client.callTool({ name: "pause_resume", arguments: { campaign_id: "7", action: "pause" } })).isError, false);
  assert.deepEqual(JSON.parse(log[0].init.body), { status: "PAUSED" });
  assert.equal(log[0].init.headers["X-RestLi-Method"], "PARTIAL_UPDATE");
  const bad = await client.callTool({ name: "pause_resume", arguments: { campaign_id: "7", action: "stop" } });
  assert.equal(bad.isError, true);
  assert.equal((await client.callTool({ name: "list_campaigns", arguments: { account_id: "9", limit: 10 } })).isError, false);
  assert.equal(log[1].url, "https://api.adz.example/adCampaigns?q=search&search=(status:(values:List(ACTIVE)))&count=10");
  assert.equal((await client.callTool({ name: "update_budget", arguments: { account_id: "9", campaign_id: "5", daily_budget: 1200 } })).isError, false);
  assert.deepEqual(JSON.parse(log[2].init.body), [{ id: "5", daily_spend_cap: 1200 }]);
  assert.equal((await client.callTool({ name: "update_budget", arguments: { account_id: "9", campaign_id: "5", daily_budget: 12.5 } })).isError, true);
});

test("fmt templates and ISO date parts (wire)", async () => {
  const spec = { id: "gads", category: "ads", label: "G", docs_url: "https://docs.example/", verified_at: "2026-09-24",
    adapter: { base_url: "https://g.example", rate_per_second: 50, auth: { type: "bearer", field: "token", fields: [{ name: "token" }] },
      tools: { pause_resume: { method: "POST", path: "/customers/{cid}/campaigns:mutate", path_params: { cid: "@customer_id" },
        body: { "operations.0.update.resourceName": "fmt:customers/{@customer_id}/campaigns/{campaign_id}", "operations.0.update.status": "map:action:pause=PAUSED,resume=ENABLED", "operations.0.updateMask": "=status" },
        result: { fields: { campaign_id: "results.0.resourceName", status: "=updated" } } },
        get_report: { path: "/analytics?q=analytics", query_safe: "(),:", params: { dateRange: "fmt:(start:(year:{year:date_from},month:{month:date_from},day:{day:date_from}))" } } } } };
  const log = [];
  const fetcher = async (url, init) => { log.push({ url, init }); return jsonResp(200, url.includes("mutate") ? { results: [{ resourceName: "customers/111/campaigns/7" }] } : { elements: [] }); };
  const server = buildServer(spec, new Transport(spec.adapter.base_url, spec.adapter.auth, { token: "TOKEN-9", customer_id: "111" }, 50, "test", fetcher));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  assert.equal((await client.callTool({ name: "pause_resume", arguments: { campaign_id: "7", action: "pause" } })).isError, false);
  assert.deepEqual(JSON.parse(log[0].init.body), { operations: [{ update: { resourceName: "customers/111/campaigns/7", status: "PAUSED" }, updateMask: "status" }] });
  await client.callTool({ name: "get_report", arguments: { account_id: "1", date_from: "2026-09-01", date_to: "2026-09-24" } });
  assert.ok(log[1].url.endsWith("dateRange=(start:(year:2026,month:9,day:1))"), log[1].url);
});


test("HMAC signing: signed query (Binance style) and signed headers over the exact body with a code-0 envelope (Bybit style) (wire)", async () => {
  const bnx = { id: "bnx", category: "trading", label: "Bnx", docs_url: "https://docs.example/", verified_at: "2026-09-24",
    adapter: { base_url: "https://api.bnx.example", rate_per_second: 50,
      auth: { type: "header", header: "X-MBX-APIKEY", field: "api_key", fields: [{ name: "api_key" }, { name: "api_secret" }], sign: { payload: "{query}", key_field: "api_secret", timestamp_param: "timestamp", signature_param: "signature" } },
      tools: { get_balances: { path: "/api/v3/account", fixed_params: { omitZeroBalances: "true" }, result: { items: "balances", key: "balances", fields: { asset: "asset", free: "free" } } } } } };
  const log = [];
  const f1 = async (url, init) => { log.push({ url, init }); return jsonResp(200, { balances: [{ asset: "BTC", free: "1.0" }] }); };
  let server = buildServer(bnx, new Transport(bnx.adapter.base_url, bnx.adapter.auth, { api_key: "KEY-abcdef", api_secret: "SECRET-abcdef" }, 50, "test", f1));
  let [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  let client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  assert.equal((await client.callTool({ name: "get_balances", arguments: {} })).isError, false);
  const q = log[0].url.split("?")[1]; const cut = q.lastIndexOf("&signature=");
  const signed = q.slice(0, cut), sig = q.slice(cut + 11);
  assert.ok(signed.startsWith("omitZeroBalances=true&timestamp="));
  assert.equal(sig, crypto.createHmac("sha256", "SECRET-abcdef").update(signed).digest("hex"));
  assert.equal(log[0].init.headers["X-MBX-APIKEY"], "KEY-abcdef");

  const byb = { id: "byb", category: "trading", label: "Byb", docs_url: "https://docs.example/", verified_at: "2026-09-24",
    adapter: { base_url: "https://api.byb.example", rate_per_second: 50, envelope: { ok_field: "retCode", ok_value: 0, error_field: "retMsg" },
      auth: { type: "none", fields: [{ name: "api_key" }, { name: "api_secret" }], sign: { payload: "{timestamp}{@api_key}5000{body}", key_field: "api_secret", headers: { "X-BAPI-API-KEY": "{@api_key}", "X-BAPI-TIMESTAMP": "{timestamp}", "X-BAPI-RECV-WINDOW": "5000", "X-BAPI-SIGN": "{signature}" } } },
      tools: { cancel_order: { method: "POST", path: "/v5/order/cancel", body: { category: "=spot", symbol: "symbol", orderId: "order_id" }, result: { root: "result", fields: { order_id: "orderId", status: "=cancelled" } } } } } };
  const log2 = []; let n = 0;
  const f2 = async (url, init) => { log2.push({ url, init }); n += 1; return jsonResp(200, n === 1 ? { retCode: 0, retMsg: "OK", result: { orderId: "o1" } } : { retCode: 110001, retMsg: "order not exists" }); };
  server = buildServer(byb, new Transport(byb.adapter.base_url, byb.adapter.auth, { api_key: "KEY-abcdef", api_secret: "SECRET-abcdef" }, 50, "test", f2, byb.adapter.envelope));
  [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  const ok = await client.callTool({ name: "cancel_order", arguments: { order_id: "o1", symbol: "BTCUSDT" } });
  assert.equal(ok.isError, false);
  const h = log2[0].init.headers;
  assert.equal(h["X-BAPI-SIGN"], crypto.createHmac("sha256", "SECRET-abcdef").update(`${h["X-BAPI-TIMESTAMP"]}KEY-abcdef5000${log2[0].init.body}`).digest("hex"));
  const bad = await client.callTool({ name: "cancel_order", arguments: { order_id: "o2", symbol: "BTCUSDT" } });
  assert.equal(bad.isError, true);
});

test("jsonstr content and session token as a query parameter (wire)", async () => {
  const spec = { id: "wc2", category: "messaging", label: "Wc2", docs_url: "https://docs.example/", verified_at: "2026-09-24",
    adapter: { base_url: "https://qy.example/cgi-bin", rate_per_second: 50, envelope: { ok_field: "errcode", ok_value: 0, error_field: "errmsg" },
      auth: { type: "session", login: { method: "GET", path: "/gettoken", body: { corpid: "@corp_id", corpsecret: "@corp_secret" } }, token_path: "access_token", token_param: "access_token", fields: [{ name: "corp_id" }, { name: "corp_secret" }] },
      tools: { send: { method: "POST", path: "/message/send", body: { touser: "to", msgtype: "=text", content: 'jsonstr:{"text": {text}}' }, result: { fields: { message_id: "msgid", status: "=sent" } } } } } };
  const log = [];
  const fetcher = async (url, init) => { log.push({ url, init }); return url.includes("gettoken") ? jsonResp(200, { access_token: "ACCESS-wc2", expires_in: 7200 }) : jsonResp(200, { errcode: 0, errmsg: "ok", msgid: "m1" }); };
  const server = buildServer(spec, new Transport(spec.adapter.base_url, spec.adapter.auth, { corp_id: "CORP-1", corp_secret: "CSECRET-1" }, 50, "test", fetcher, spec.adapter.envelope));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  const text = 'He said "hi"\nnext line \\ done';
  assert.equal((await client.callTool({ name: "send", arguments: { to: "u1", text } })).isError, false);
  const send = log.find((l) => l.url.includes("/message/send"));
  assert.equal(new URL(send.url).searchParams.get("access_token"), "ACCESS-wc2");
  assert.equal(send.init.headers.Authorization, undefined);
  assert.deepEqual(JSON.parse(JSON.parse(send.init.body).content), { text });
});


test("map to a typed boolean (wire)", async () => {
  const spec = { id: "ob", category: "ads", label: "Ob", docs_url: "https://docs.example/", verified_at: "2026-09-25",
    adapter: { base_url: "https://ob.example", rate_per_second: 50, auth: { type: "none", fields: [] },
      tools: { pause_resume: { method: "PUT", path: "/campaigns/{campaign_id}", body: { enabled: "map:action:pause=json:false,resume=json:true" }, result: { fields: { campaign_id: "id", status: "=updated" } } } } } };
  const log = [];
  const server = buildServer(spec, new Transport(spec.adapter.base_url, spec.adapter.auth, {}, 50, "test", async (url, init) => { log.push(init); return jsonResp(200, { id: "7" }); }));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  assert.equal((await client.callTool({ name: "pause_resume", arguments: { campaign_id: "7", action: "resume" } })).isError, false);
  assert.deepEqual(JSON.parse(log[0].body), { enabled: true });
});

// ---- 2026-09-25 runtime features: dates, money, dynamic keys, keyed lists, cursors, XML, token options, signing modes
const WAVE = { id: "wv", category: "ecommerce_channels", label: "Wv", docs_url: "https://docs.example/", verified_at: "2026-09-25",
  adapter: { base_url: "https://wv.example", rate_per_second: 50, auth: { type: "none", fields: [] },
    tools: {
      list_orders: { path: "/orders", params: { from: "epoch:since", from_ms: "epoch_ms:since", d: "datefmt:%m/%d/%Y:since", to: "days_ahead:0", after: "cursor" },
        result: { items: "data.orders", items_are_values: true, key: "orders", next_cursor: "data.next", fields: { order_id: "_key", status: "st" } } },
      update_listing: { method: "PUT", path: "/items", body: { "updates.{listing_id}.price_cents": "minor:price", "updates.{listing_id}.budget_micros": "micros:price", k: "mul:1000:price" }, result: { fields: { listing_id: "=ok", status: "=updated" } } },
      set_inventory: { method: "POST", path: "/stock", body_format: "xml", xml_root: "Request", body: { "Product.SellerSku": "sku", "Product.Quantity": "quantity", "Product.@op": "=set" },
        result: { root: "Response.Head", fields: { listing_id: "RequestId", status: "Status" } } } } } };

async function wireClient(spec, transport) {
  const server = buildServer(spec, transport);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("dates, cursors, keyed lists, money units, dynamic keys and XML (wire)", async () => {
  const log = [];
  const fetcher = async (url, init) => {
    log.push({ url, init });
    if (url.includes("/orders")) return jsonResp(200, { data: { orders: { A1: { st: "new" }, A2: { st: "paid" } }, next: "tok2" } });
    if (url.includes("/stock")) return { status: 200, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/xml" : null) }, text: async () => '<?xml version="1.0"?><Response><Head><RequestId>r-1</RequestId><Status>ok</Status></Head></Response>' };
    return { status: 204, headers: { get: () => null }, text: async () => "" };
  };
  const client = await wireClient(WAVE, new Transport(WAVE.adapter.base_url, WAVE.adapter.auth, {}, 50, "test", fetcher));
  const res = await client.callTool({ name: "list_orders", arguments: { since: "2026-09-01", cursor: "tok1" } });
  assert.deepEqual(res.structuredContent.orders.map((o) => o.order_id), ["A1", "A2"]);
  assert.equal(res.structuredContent.next_cursor, "tok2");
  const q = new URL(log[0].url).searchParams;
  assert.equal(q.get("from"), "1788220800"); assert.equal(q.get("from_ms"), "1788220800000"); assert.equal(q.get("d"), "09/01/2026"); assert.equal(q.get("after"), "tok1");
  assert.match(q.get("to"), /^\d{4}-\d{2}-\d{2}$/);
  assert.equal((await client.callTool({ name: "update_listing", arguments: { listing_id: "SKU-9", price: 19.995 } })).isError, false);
  assert.deepEqual(JSON.parse(log[1].init.body), { updates: { "SKU-9": { price_cents: 2000, budget_micros: 19995000 } }, k: 19995 });
  const inv = await client.callTool({ name: "set_inventory", arguments: { sku: "S&1", quantity: 4 } });
  assert.equal(inv.structuredContent.listing_id, "r-1");
  assert.equal(log[2].init.body, '<?xml version="1.0" encoding="UTF-8"?><Request><Product op="set"><SellerSku>S&amp;1</SellerSku><Quantity>4</Quantity></Product></Request>');
  assert.equal(log[2].init.headers["Content-Type"], "application/xml");
});

test("token URL placeholders, GET token, token headers, nested login and header tokens (wire)", async () => {
  const spec = { id: "tk", category: "messaging", label: "Tk", docs_url: "https://docs.example/", verified_at: "2026-09-25",
    adapter: { base_url: "https://{region}.tk.example", rate_per_second: 50,
      auth: { type: "oauth2_client_credentials", token_url: "https://{region}.tk.example/token", token_method: "GET", client_auth: "body", token_headers: { "WM_SVC.NAME": "platform-mcp", "X-Key": "{@client_id}" }, fields: [{ name: "client_id" }, { name: "client_secret" }] },
      config_fields: [{ name: "region" }], tools: { me: { kind: "probe", path: "/me" } } } };
  const log = [];
  const fetcher = async (url, init) => {
    log.push({ url, init });
    if (url.includes("/token")) return jsonResp(200, { access_token: "ACCESS-tk", expires_in: 900 });
    if (url.endsWith("/login")) return { status: 204, headers: { get: (k) => (k === "X-Auth-Token" ? "SESSION-tk" : null) }, text: async () => "" };
    return jsonResp(200, { id: 1 });
  };
  let client = await wireClient(spec, new Transport(spec.adapter.base_url, spec.adapter.auth, { client_id: "CID-1", client_secret: "SECRET-tk", region: "eu" }, 50, "test", fetcher));
  assert.equal((await client.callTool({ name: "me", arguments: {} })).isError, false);
  const tu = new URL(log[0].url);
  assert.equal(tu.host, "eu.tk.example"); assert.equal(log[0].init.method, "GET");
  assert.equal(tu.searchParams.get("client_id"), "CID-1"); assert.equal(log[0].init.headers["X-Key"], "CID-1");
  assert.equal(log[1].init.headers.Authorization, "Bearer ACCESS-tk");
  const s2 = JSON.parse(JSON.stringify(spec));
  s2.adapter.auth = { type: "session", login: { method: "POST", path: "/login", body: { "auth.user": "@user", "auth.pass": "@password" }, headers: { "X-App": "{@app}" } }, token_from_header: "X-Auth-Token", prefix: "", header: "X-Auth-Token", fields: [{ name: "user" }, { name: "password" }] };
  log.length = 0;
  client = await wireClient(s2, new Transport(s2.adapter.base_url, s2.adapter.auth, { user: "u", password: "PASSWORD-tk", region: "eu", app: "APP-1" }, 50, "test", fetcher));
  assert.equal((await client.callTool({ name: "me", arguments: {} })).isError, false);
  assert.deepEqual(JSON.parse(log[0].init.body), { auth: { user: "u", pass: "PASSWORD-tk" } });
  assert.equal(log[0].init.headers["X-App"], "APP-1");
  assert.equal(log[1].init.headers["X-Auth-Token"], "SESSION-tk");
});

test("signing modes: md5 hash upper over sorted params, JWT HS256 and RS256 (wire)", async () => {
  const spec = { id: "sg", category: "ecommerce_channels", label: "Sg", docs_url: "https://docs.example/", verified_at: "2026-09-25",
    adapter: { base_url: "https://sg.example", rate_per_second: 50,
      auth: { type: "none", fields: [{ name: "app_key" }, { name: "app_secret" }], sign: { mode: "hash", algorithm: "md5", case: "upper", payload: "{@app_secret}{sorted_params}{@app_secret}", timestamp_param: "timestamp", params: { app_key: "{@app_key}" }, signature_param: "sign" } },
      tools: { list_orders: { path: "/orders", params: { status: "status" }, result: { items: "orders", key: "orders", fields: { order_id: "id" } } } } } };
  const log = [];
  const fetcher = async (url, init) => { log.push({ url, init }); return jsonResp(200, { orders: [] }); };
  let client = await wireClient(spec, new Transport(spec.adapter.base_url, spec.adapter.auth, { app_key: "KEY-sg", app_secret: "SECRET-sg" }, 50, "test", fetcher));
  assert.equal((await client.callTool({ name: "list_orders", arguments: { status: "paid" } })).isError, false);
  const params = Object.fromEntries(new URL(log[0].url).searchParams); const sig = params.sign; delete params.sign;
  const sorted = Object.keys(params).sort().map((k) => k + params[k]).join("");
  assert.equal(sig, crypto.createHash("md5").update(`SECRET-sg${sorted}SECRET-sg`).digest("hex").toUpperCase());
  const { privateKey, publicKey } = crypto.generateKeyPairSync("rsa", { modulusLength: 2048 });
  for (const [mode, secret, verify] of [["jwt_hs256", "SECRET-jwt-0123456789-abcdefghijklmnop", null], ["jwt_rs256", privateKey.export({ type: "pkcs8", format: "pem" }), publicKey]]) {
    const s3 = JSON.parse(JSON.stringify(spec));
    s3.adapter.auth = { type: "none", fields: [{ name: "api_key" }, { name: "api_secret" }], sign: { mode, key_field: "api_secret", claims: { iss: "{@api_key}", iat: "{timestamp_s}", exp: "+300" }, jwt_header: { kid: "k1" }, headers: { Authorization: "Bearer {signature}" } } };
    log.length = 0;
    client = await wireClient(s3, new Transport(s3.adapter.base_url, s3.adapter.auth, { api_key: "KEY-jwt", api_secret: secret }, 50, "test", fetcher));
    assert.equal((await client.callTool({ name: "list_orders", arguments: {} })).isError, false);
    const [h, p, s] = log[0].init.headers.Authorization.split(" ")[1].split(".");
    const claims = JSON.parse(Buffer.from(p, "base64url")); const header = JSON.parse(Buffer.from(h, "base64url"));
    assert.equal(claims.iss, "KEY-jwt"); assert.equal(claims.exp - claims.iat, 300); assert.equal(header.kid, "k1");
    if (mode === "jwt_hs256") assert.equal(s, crypto.createHmac("sha256", secret).update(`${h}.${p}`).digest("base64url"));
    else assert.ok(crypto.createVerify("RSA-SHA256").update(`${h}.${p}`).verify(verify, Buffer.from(s, "base64url")));
  }
});

// ---- 2026-09-25 (2): signing variants, AWS SigV4, OAuth 1.0a, body-field signatures, token field renames
function sg2(auth, fetcher, creds = {}, tools, base = "https://api.sg2.example") {
  const spec = { id: "sg2", category: "ecommerce_channels", label: "Sg2", docs_url: "https://docs.example/", verified_at: "2026-09-25",
    adapter: { base_url: base, rate_per_second: 50, auth, tools: tools ?? { list_orders: { path: "/rest/orders/get", params: { status: "status" }, result: { items: "orders", key: "orders", fields: { order_id: "id" } } } } } };
  return wireClient(spec, new Transport(base, auth, creds, 50, "test", fetcher));
}

test("AWS SigV4 matches the AWS get-vanilla vector; timezone timestamps, path strip, sorted forms, pre digests (wire)", async () => {
  const realNow = Date.now; Date.now = () => 1440938160000;
  try {
    const log = []; const f = async (url, init) => { log.push({ url, init }); return jsonResp(200, {}); };
    const c = await sg2({ type: "none", fields: [{ name: "access_key_id" }, { name: "secret_access_key" }], sign: { mode: "aws_sigv4", service: "service", region: "us-east-1" } }, f,
      { access_key_id: "AKIDEXAMPLE", secret_access_key: "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY" }, { me: { kind: "probe", path: "/" } }, "https://example.amazonaws.com");
    assert.equal((await c.callTool({ name: "me", arguments: {} })).isError, false);
    assert.equal(log[0].init.headers["X-Amz-Date"], "20150830T123600Z");
    assert.equal(log[0].init.headers.Authorization, "AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/20150830/us-east-1/service/aws4_request, SignedHeaders=host;x-amz-date, Signature=5fa00fa31553b73ebf1942676e86291e8372ff2a2260956d9b8aae1d763fbf31");
    Date.now = () => 1790301600000;
    const log2 = []; const f2 = async (url, init) => { log2.push({ url, init }); return jsonResp(200, { orders: [] }); };
    const auth = { type: "none", fields: [{ name: "app_key" }, { name: "app_secret" }], sign: { mode: "hmac", algorithm: "sha256", case: "upper", key_field: "app_secret", path_strip: "/rest",
      timestamp_param: "timestamp", timestamp_value: "timestamp_fmt", timestamp_format: "%Y-%m-%d %H:%M:%S", timestamp_offset: "+08:00", params: { app_key: "{@app_key}" },
      payload: "{path}{sorted_params}|{sorted_values}|{sorted_kv}", pre: [{ name: "ts_md5", mode: "hash", algorithm: "md5", payload: "{timestamp_s}" }], headers: { token: "{ts_md5}" }, signature_param: "sign" } };
    const c2 = await sg2(auth, f2, { app_key: "KEY-1", app_secret: "SECRET-1" });
    assert.equal((await c2.callTool({ name: "list_orders", arguments: { status: "paid" } })).isError, false);
    const q = Object.fromEntries(new URL(log2[0].url).searchParams); const sig = q.sign; delete q.sign;
    assert.equal(q.timestamp, new Date(1790301600000 + 8 * 3600000).toISOString().slice(0, 19).replace("T", " "));
    const kv = Object.keys(q).sort().map((k) => [k, q[k]]);
    const payload = "/orders/get" + kv.map(([k, v]) => k + v).join("") + "|" + kv.map(([, v]) => v).join("") + "|" + kv.map(([k, v]) => `${k}=${v}`).join("");
    assert.equal(sig, crypto.createHmac("sha256", "SECRET-1").update(payload).digest("hex").toUpperCase());
    assert.equal(log2[0].init.headers.token, crypto.createHash("md5").update("1790301600").digest("hex"));
  } finally { Date.now = realNow; }
});

test("OAuth 1.0a, body-field signatures, RSA-SHA256, JWT with decoded key and templated kid, token field renames (wire)", async () => {
  const log = []; const f = async (url, init) => { log.push({ url, init }); return url.includes("refresh_token") ? jsonResp(200, { code: 0, data: { access_token: "ACCESS-oe", refresh_token: "REFRESH-oe-2", expires_in: 86400 } }) : jsonResp(200, { orders: [], ok: true, id: 1 }); };
  const e = (x) => encodeURIComponent(String(x)).replace(/[!'()*]/g, (c) => "%" + c.charCodeAt(0).toString(16).toUpperCase());
  let c = await sg2({ type: "none", fields: [], sign: { mode: "oauth1" } }, f, { consumer_key: "CK-1", consumer_secret: "CS-1&x", access_token: "AT-1", access_token_secret: "ATS-1" });
  assert.equal((await c.callTool({ name: "list_orders", arguments: { status: "a b" } })).isError, false);
  const oauth = Object.fromEntries(log[0].init.headers.Authorization.slice(6).split(", ").map((x) => { const i = x.indexOf("="); return [x.slice(0, i), x.slice(i + 2, -1)]; }));
  const sig = decodeURIComponent(oauth.oauth_signature); delete oauth.oauth_signature;
  const params = [[e("status"), e("a b")], ...Object.entries(oauth)].sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
  const base = ["GET", e("https://api.sg2.example/rest/orders/get"), e(params.map(([k, v]) => `${k}=${v}`).join("&"))].join("&");
  assert.equal(sig, crypto.createHmac("sha1", `${e("CS-1&x")}&${e("ATS-1")}`).update(base).digest("base64"));
  log.length = 0;
  c = await sg2({ type: "none", fields: [], sign: { mode: "hash", algorithm: "md5", case: "upper", payload: "{@app_secret}{sorted_body}{@app_secret}", body_field: "sign" } }, f, { app_secret: "SECRET-t" },
    { update_listing: { method: "POST", path: "/api", body: { type: "=bg.goods.update", goods_id: "listing_id", price: "str:price" }, result: { fields: { listing_id: "=x", status: "=updated" } } } });
  assert.equal((await c.callTool({ name: "update_listing", arguments: { listing_id: "G1", price: 9.5 } })).isError, false);
  const body = JSON.parse(log[0].init.body); const bsig = body.sign; delete body.sign;
  assert.equal(bsig, crypto.createHash("md5").update("SECRET-t" + Object.keys(body).sort().map((k) => k + body[k]).join("") + "SECRET-t").digest("hex").toUpperCase());
  const { privateKey, publicKey } = crypto.generateKeyPairSync("rsa", { modulusLength: 2048 });
  log.length = 0;
  c = await sg2({ type: "none", fields: [], sign: { mode: "rsa_sha256", payload: "{method}\n{path}\n{timestamp}", headers: { "X-Sig": "{signature}", "X-Ts": "{timestamp}" } } }, f, { private_key: privateKey.export({ type: "pkcs8", format: "pem" }) });
  assert.equal((await c.callTool({ name: "list_orders", arguments: {} })).isError, false);
  const h = log[0].init.headers;
  assert.ok(crypto.createVerify("RSA-SHA256").update(`GET\n/rest/orders/get\n${h["X-Ts"]}`).verify(publicKey, Buffer.from(h["X-Sig"], "base64")));
  const raw = Buffer.from("\x01\x02binary-secret-0123456789abcdefghij", "latin1");
  log.length = 0;
  c = await sg2({ type: "none", fields: [], sign: { mode: "jwt_hs256", key_encoding: "base64url", claims: { iss: "dev" }, jwt_header: { kid: "{@kid}" }, headers: { Authorization: "Bearer {signature}" } } }, f, { api_secret: raw.toString("base64url"), kid: "KID-7" });
  assert.equal((await c.callTool({ name: "list_orders", arguments: {} })).isError, false);
  const [hh, pp, ss] = log[0].init.headers.Authorization.split(" ")[1].split(".");
  assert.equal(JSON.parse(Buffer.from(hh, "base64url")).kid, "KID-7");
  assert.equal(ss, crypto.createHmac("sha256", raw).update(`${hh}.${pp}`).digest("base64url"));
  log.length = 0;
  const auth = { type: "oauth2_refresh_token", token_url: "https://ad.example/oauth2/refresh_token", client_auth: "body", token_body: "json", token_fields: { client_id: "app_id", client_secret: "secret", grant_type: null },
    token_path: "data.access_token", refresh_token_path: "data.refresh_token", expires_path: "data.expires_in", header: "Access-Token", prefix: "", fields: [{ name: "client_id" }, { name: "client_secret" }, { name: "refresh_token" }] };
  const t = new Transport("https://ad.example", auth, { client_id: "APP-1", client_secret: "SECRET-oe", refresh_token: "REFRESH-oe-1" }, 50, "test", f);
  c = await wireClient({ id: "oe", category: "ads", label: "Oe", docs_url: "https://docs.example/", verified_at: "2026-09-25", adapter: { base_url: "https://ad.example", rate_per_second: 50, auth, tools: { me: { kind: "probe", path: "/me" } } } }, t);
  assert.equal((await c.callTool({ name: "me", arguments: {} })).isError, false);
  assert.deepEqual(JSON.parse(log[0].init.body), { refresh_token: "REFRESH-oe-1", app_id: "APP-1", secret: "SECRET-oe" });
  assert.equal(log[1].init.headers["Access-Token"], "ACCESS-oe");
  assert.equal(t.creds.refresh_token, "REFRESH-oe-2");
});

// ---- 2026-09-25 (3): multipart uploads, cookie sessions, signed token requests, cookie-returned tokens
test("multipart with a downloaded file, cookie sessions and cookie-returned tokens (wire)", async () => {
  const log = [];
  const f = async (url, init) => {
    log.push({ url, init });
    if (url === "https://cdn.example/cat.png") return { status: 200, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "image/png" : null) }, arrayBuffer: async () => new TextEncoder().encode("PNGDATA").buffer, text: async () => "PNGDATA" };
    if (url.endsWith("/login")) return { status: 200, headers: { get: (k) => (k.toLowerCase() === "set-cookie" ? "SESSION=SESS-mp; Path=/; HttpOnly" : "application/json") }, text: async () => JSON.stringify({ ok: true }) };
    return jsonResp(200, { id: "j1", status: "queued" });
  };
  const auth = { type: "session", login: { method: "POST", path: "/login", body: { u: "@user", p: "@password" } }, token_from_cookie: "SESSION", header: "", cookies: { SESSION: "{access_token}", uid: "{nonce}" }, fields: [{ name: "user" }, { name: "password" }] };
  const spec = { id: "mp", category: "builder_tools", label: "Mp", docs_url: "https://docs.example/", verified_at: "2026-09-25",
    adapter: { base_url: "https://mp.example", rate_per_second: 50, auth, tools: { generate_image: { method: "POST", path: "/v2/generate", body_format: "multipart", body: { prompt: "prompt", image: "file:image_url", output_format: "=png" }, result: { fields: { job_id: "id", status: "status" } } } } } };
  const t = new Transport(spec.adapter.base_url, auth, { user: "u", password: "PASSWORD-mp" }, 50, "test", f);
  t.resolveHost = async () => ["93.184.215.14"]; // the download guard resolves the host (netguard.ts); cdn.example is public here
  const c = await wireClient(spec, t);
  const res = await c.callTool({ name: "generate_image", arguments: { prompt: "a cat", image_url: "https://cdn.example/cat.png" } });
  assert.equal(res.isError, false);
  const gen = log.find((l) => l.url.endsWith("/v2/generate"));
  assert.ok(gen.init.body instanceof FormData);
  assert.equal(gen.init.body.get("prompt"), "a cat"); assert.equal(gen.init.body.get("output_format"), "png");
  const file = gen.init.body.get("image"); assert.equal(file.name, "cat.png"); assert.equal(Buffer.from(await file.arrayBuffer()).toString(), "PNGDATA");
  assert.ok(!Object.keys(gen.init.headers).some((h) => h.toLowerCase() === "content-type"));
  assert.match(gen.init.headers.Cookie, /^SESSION=SESS-mp; uid=[0-9a-f]{32}$/); assert.equal(gen.init.headers.Authorization, undefined);
});

test("signed token refresh and the minted token inside the request signature (Shopee style, wire)", async () => {
  const realNow = Date.now; Date.now = () => 1790301600000;
  try {
    const log = [];
    const f = async (url, init) => { log.push({ url, init }); return url.includes("/auth/access_token/get") ? jsonResp(200, { access_token: "ACCESS-sp", refresh_token: "REFRESH-sp-2", expire_in: 14400 }) : jsonResp(200, { response: { order_list: [] } }); };
    const auth = { type: "oauth2_refresh_token", token_url: "https://partner.shopee.example/api/v2/auth/access_token/get", token_body: "json", client_auth: "body",
      token_fields: { client_id: null, client_secret: null, grant_type: null }, expires_path: "expire_in", header: "", token_param: "access_token",
      token_sign: { mode: "hmac", algorithm: "sha256", key_field: "partner_key", payload: "{@partner_id}{path}{timestamp_s}" },
      token_query: { partner_id: "{@partner_id}", timestamp: "{timestamp_s}", sign: "{signature}" }, token_body_extra: { partner_id: "int:{@partner_id}", shop_id: "int:{@shop_id}" },
      sign: { mode: "hmac", algorithm: "sha256", key_field: "partner_key", payload: "{@partner_id}{path}{timestamp_s}{access_token}{@shop_id}", params: { partner_id: "{@partner_id}", shop_id: "{@shop_id}", timestamp: "{timestamp_s}" }, signature_param: "sign" },
      fields: [{ name: "client_id", required: false }, { name: "refresh_token" }, { name: "partner_key" }] };
    const spec = { id: "sp", category: "ecommerce_channels", label: "Sp", docs_url: "https://docs.example/", verified_at: "2026-09-25",
      adapter: { base_url: "https://partner.shopee.example", rate_per_second: 50, auth, tools: { list_orders: { path: "/api/v2/order/get_order_list", result: { items: "response.order_list", key: "orders", fields: { order_id: "order_sn" } } } } } };
    const c = await wireClient(spec, new Transport(spec.adapter.base_url, auth, { client_id: "x", refresh_token: "REFRESH-sp-1", partner_key: "PKEY-sp", partner_id: "1001", shop_id: "2002" }, 50, "test", f));
    assert.equal((await c.callTool({ name: "list_orders", arguments: {} })).isError, false);
    assert.deepEqual(JSON.parse(log[0].init.body), { refresh_token: "REFRESH-sp-1", partner_id: 1001, shop_id: 2002 });
    assert.equal(new URL(log[0].url).searchParams.get("sign"), crypto.createHmac("sha256", "PKEY-sp").update("1001/api/v2/auth/access_token/get1790301600").digest("hex"));
    const q = new URL(log[1].url).searchParams;
    assert.equal(q.get("access_token"), "ACCESS-sp");
    assert.equal(q.get("sign"), crypto.createHmac("sha256", "PKEY-sp").update("1001/api/v2/order/get_order_list1790301600ACCESS-sp2002").digest("hex"));
  } finally { Date.now = realNow; }
});

// ---- 2026-09-25 (4): token in path/body, several ok values, CSV, JSON multipart parts, client assertions, cookie replay, sign exclusions
test("token in path and body, ok-value lists, CSV, JSON multipart parts, sign exclusions (wire)", async () => {
  const log = [];
  const f = async (url, init) => {
    log.push({ url, init });
    if (url.endsWith("/api/login")) return jsonResp(200, { Token: "TOK-4" });
    if (url.endsWith("/api/stock/TOK-4")) return jsonResp(200, { code: "200", stock: [] });
    if (url.endsWith("/api/report")) return jsonResp(200, { code: 200, data: { id: "r1" } });
    if (url.endsWith("/api/fail")) return jsonResp(200, { code: 500, msg: "boom" });
    if (url.endsWith("/api/tenders.csv")) return { status: 200, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "text/csv; charset=utf-8" : null) }, text: async () => '﻿id,title\n1,"Roads, bridges"\n2,Water\n' };
    if (url.includes("t5.example")) return jsonResp(200, { orders: [] });
    return jsonResp(200, { code: 200, results: [] });
  };
  const auth = { type: "session", login: { method: "POST", path: "/api/login", body: { User: "@user", Password: "@password" } }, token_path: "Token", header: "", token_body_path: "header.accessToken", fields: [{ name: "user" }, { name: "password" }] };
  const env = { ok_field: "code", ok_value: ["200", 200], error_field: "msg" };
  const spec = { id: "t4", category: "deals", label: "T4", docs_url: "https://docs.example/", verified_at: "2026-09-25",
    adapter: { base_url: "https://t4.example", rate_per_second: 50, auth, envelope: env, tools: {
      me: { kind: "probe", path: "/api/stock/{access_token}" },
      get_posting: { method: "POST", path: "/api/report", body: { "body.id": "id" }, result: { root: "data", fields: { id: "id" } } },
      bid_status: { method: "POST", path: "/api/fail", body: { x: "=1" }, result: { fields: { bid_id: "id" } } },
      search_postings: { path: "/api/tenders.csv", result: { items: "rows", key: "postings", fields: { id: "id", title: "title" } } },
      list_messages: { method: "POST", path: "/api/search", body_format: "multipart", body: { query: 'jsonpart:json:{"bool":{"must":[]}}', text: "=*" }, result: { items: "results", key: "messages", fields: { id: "id" } } } } } };
  const c = await wireClient(spec, new Transport(spec.adapter.base_url, auth, { user: "u", password: "PASSWORD-4" }, 50, "test", f, env));
  assert.equal((await c.callTool({ name: "me", arguments: {} })).isError, false);
  assert.ok(log.some((l) => l.url.endsWith("/api/stock/TOK-4")));
  assert.equal((await c.callTool({ name: "get_posting", arguments: { id: "p9" } })).isError, false);
  assert.deepEqual(JSON.parse(log.find((l) => l.url.endsWith("/api/report")).init.body), { body: { id: "p9" }, header: { accessToken: "TOK-4" } });
  assert.equal((await c.callTool({ name: "bid_status", arguments: { bid_id: "b" } })).isError, true);
  const res = await c.callTool({ name: "search_postings", arguments: { query: "x" } });
  assert.deepEqual(res.structuredContent.postings.map((p) => p.title), ["Roads, bridges", "Water"]);
  assert.equal((await c.callTool({ name: "list_messages", arguments: {} })).isError, false);
  const part = log.find((l) => l.url.endsWith("/api/search")).init.body.get("query");
  assert.equal(part.type, "application/json"); assert.deepEqual(JSON.parse(await part.text()), { bool: { must: [] } });
  const sg = { type: "none", fields: [{ name: "app_secret" }], sign: { mode: "hash", algorithm: "md5", payload: "{@app_secret}{sorted_params}{@app_secret}", params: { access_token: "AT", sign_method: "md5", app_key: "K" }, exclude: ["access_token", "sign_method"], signature_param: "sign" } };
  const spec2 = { id: "t5", category: "deals", label: "T5", docs_url: "https://docs.example/", verified_at: "2026-09-25", adapter: { base_url: "https://t5.example", rate_per_second: 50, auth: sg, tools: { search_postings: { path: "/orders", result: { items: "orders", key: "postings", fields: { id: "id" } } } } } };
  const c2 = await wireClient(spec2, new Transport("https://t5.example", sg, { app_secret: "S5" }, 50, "test", f));
  assert.equal((await c2.callTool({ name: "search_postings", arguments: { query: "q" } })).isError, false);
  assert.equal(new URL(log[log.length - 1].url).searchParams.get("sign"), crypto.createHash("md5").update("S5app_keyKS5").digest("hex"));
});

test("JWT client assertion in the token request and every login cookie replayed (wire)", async () => {
  const { privateKey, publicKey } = crypto.generateKeyPairSync("rsa", { modulusLength: 2048 });
  const pem = privateKey.export({ type: "pkcs8", format: "pem" });
  const log = [];
  const f = async (url, init) => {
    log.push({ url, init });
    if (url.endsWith("/oauth2/token")) return jsonResp(200, { access_token: "ACCESS-ca", expires_in: 600 });
    if (url.endsWith("/login")) return { status: 200, headers: { get: (k) => (k.toLowerCase() === "set-cookie" ? "a=1; Path=/, b=2; Path=/" : "application/json") }, text: async () => "{}" };
    return jsonResp(200, { id: 1 });
  };
  const verify = (jwt) => { const [h, p, s] = jwt.split("."); assert.ok(crypto.createVerify("RSA-SHA256").update(`${h}.${p}`).verify(publicKey, Buffer.from(s, "base64url"))); return [JSON.parse(Buffer.from(h, "base64url")), JSON.parse(Buffer.from(p, "base64url"))]; };
  const auth = { type: "oauth2_client_credentials", token_url: "https://id.example/oauth2/token", client_auth: "body",
    token_jwt: { mode: "jwt_rs256", key_field: "private_key", claims: { iss: "{@client_id}", sub: "{@client_id}", aud: "https://id.example/oauth2/token", exp: "+600", jti: "{nonce}" }, jwt_header: { kid: "{@kid}" } },
    token_fields: { client_secret: null }, token_params: { client_assertion_type: "urn:ietf:params:oauth:client-assertion-type:jwt-bearer", client_assertion: "{client_assertion}" }, fields: [{ name: "client_id" }, { name: "private_key" }, { name: "kid" }] };
  const spec = { id: "ca", category: "ads", label: "Ca", docs_url: "https://docs.example/", verified_at: "2026-09-25", adapter: { base_url: "https://dsp.example", rate_per_second: 50, auth, tools: { me: { kind: "probe", path: "/me" } } } };
  let c = await wireClient(spec, new Transport("https://dsp.example", auth, { client_id: "CID-ca", private_key: pem, kid: "k9" }, 50, "test", f));
  assert.equal((await c.callTool({ name: "me", arguments: {} })).isError, false);
  const form = new URLSearchParams(log[0].init.body);
  const [hdr, claims] = verify(form.get("client_assertion"));
  assert.equal(claims.iss, "CID-ca"); assert.equal(hdr.kid, "k9"); assert.equal(form.get("client_secret"), null);
  assert.equal(log[1].init.headers.Authorization, "Bearer ACCESS-ca");
  log.length = 0;
  const a2 = { type: "session", login: { method: "POST", path: "/login", body: { token: "{client_assertion}" } }, token_from_cookie: "*", header: "",
    token_jwt: { mode: "jwt_rs256", key_field: "private_key", claims: { sub: "{@client_id}", iat: "{timestamp_s}" } }, fields: [{ name: "client_id" }, { name: "private_key" }] };
  c = await wireClient({ ...spec, adapter: { ...spec.adapter, base_url: "https://noon.example", auth: a2 } }, new Transport("https://noon.example", a2, { client_id: "CID-n", private_key: pem }, 50, "test", f));
  assert.equal((await c.callTool({ name: "me", arguments: {} })).isError, false);
  assert.equal(verify(JSON.parse(log[0].init.body).token)[1].sub, "CID-n");
  assert.equal(log[1].init.headers.Cookie, "a=1; b=2");
});
