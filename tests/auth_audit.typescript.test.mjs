// Vendor-published signing vectors and the auth-audit fixes, TypeScript runtime (same cases as
// tests/test_auth_audit_python.py; sources are cited there and in docs/AUTH_AUDIT.md).
import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const entry = (rel) => JSON.parse(readFileSync(new URL(`../catalog/${rel}`, import.meta.url), "utf8"));
const resp = (status, body) => ({ status, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null) }, text: async () => JSON.stringify(body) });

async function wire(spec, creds, body = {}) {
  const log = [];
  const fetcher = async (url, init) => { log.push({ url: String(url), init }); return resp(200, typeof body === "function" ? body(String(url)) : body); };
  const a = spec.adapter;
  const t = new Transport(a.base_url, a.auth, { ...creds }, 50, "test", fetcher, a.envelope ?? {});
  t.fixedHeaders = a.headers ?? {};
  const server = buildServer(spec, t);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return { client, log };
}
const synth = (auth, tools, base, category = "ecommerce_channels", headers = {}) => ({ id: "vec", category, label: "Vec", docs_url: "https://docs.example/", verified_at: "2026-09-26", adapter: { base_url: base, rate_per_second: 50, auth, tools, headers } });

async function withClock(ms, uuid, fn) {
  const realNow = Date.now; const realUuid = crypto.randomUUID;
  Date.now = () => ms;
  if (uuid) crypto.randomUUID = () => uuid;
  try { return await fn(); } finally { Date.now = realNow; crypto.randomUUID = realUuid; }
}

const AWS = [
  ["get-vanilla", "GET", "/", [], "5fa00fa31553b73ebf1942676e86291e8372ff2a2260956d9b8aae1d763fbf31"],
  ["get-vanilla-query-order-key-case", "GET", "/", [["Param2", "value2"], ["Param1", "value1"]], "b97d918cfa904a5beff61c982a1b6f458b799221646efd99d3219ec94cdf2500"],
  ["get-vanilla-query-unreserved", "GET", "/", [["-._~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", "-._~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"]], "9c3e54bfcdf0b19771a7f523ee5669cdf59bc7cc0884027167c21bb143a40197"],
  ["get-vanilla-empty-query-key", "GET", "/", [["Param1", "value1"]], "a67d582fa61cc504c4bae71f336f98b97f1ea3c7a6bfe1b6e45aec72011b9aeb"],
  ["get-utf8", "GET", "/ሴ", [], "8318018e0b0f223aa2bbf98705b62bb787dc9c0e678f255a891fd03141be5d85"],
  ["get-space-normalized", "GET", "/example space/", [], "652487583200325589f1fba4c7e578f72c47cb61beeca81406b39ddec1366741"],
  ["post-vanilla", "POST", "/", [], "5da7c1a2acd57cee7505fc6676e4e544621c30862966e37dddb68e92efbe5d6b"],
  ["post-vanilla-query", "POST", "/", [["Param1", "value1"]], "28038455d6de14eafc1f9222cf5aa6f1a96197d7deb8263271d420d138af7f11"],
];

for (const [name, method, path, query, sig] of AWS) {
  test(`AWS SigV4 test suite: ${name} (wire)`, () => withClock(1440938160000, null, async () => {
    const auth = { type: "none", fields: [{ name: "access_key_id" }, { name: "secret_access_key" }], sign: { mode: "aws_sigv4", service: "service", region: "us-east-1" } };
    const { client, log } = await wire(synth(auth, { me: { kind: "probe", method, path, fixed_params: Object.fromEntries(query) } }, "https://example.amazonaws.com"),
      { access_key_id: "AKIDEXAMPLE", secret_access_key: "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY" });
    assert.equal((await client.callTool({ name: "me", arguments: {} })).isError, false);
    assert.equal(log[0].init.headers["X-Amz-Date"], "20150830T123600Z");
    assert.equal(log[0].init.headers.Authorization, `AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/20150830/us-east-1/service/aws4_request, SignedHeaders=host;x-amz-date, Signature=${sig}`);
  }));
}

const oauthHeader = (h) => Object.fromEntries(h.slice(6).split(", ").map((x) => { const i = x.indexOf("="); return [x.slice(0, i), decodeURIComponent(x.slice(i + 2, -1))]; }));

test("OAuth 1.0a: OAuth Core 1.0 Appendix A.5 (wire)", () => withClock(1191242096000, "kllo9940pd9333jh", async () => {
  const { client, log } = await wire(synth({ type: "none", fields: [], sign: { mode: "oauth1" } }, { me: { kind: "probe", path: "/photos", fixed_params: { file: "vacation.jpg", size: "original" } } }, "http://photos.example.net"),
    { consumer_key: "dpf43f3p2l4k3l03", consumer_secret: "kd94hf93k423kf44", access_token: "nnch734d00sl2jdk", access_token_secret: "pfkkdhi9sl3r4s00" });
  assert.equal((await client.callTool({ name: "me", arguments: {} })).isError, false);
  assert.equal(oauthHeader(log[0].init.headers.Authorization).oauth_signature, "tR3+Ty81lMeYAr/Fid0kMTYa/WM=");
}));

test("OAuth 1.0a signs form-encoded body parameters: X docs example (wire)", () => withClock(1318622958000, "kYjzVBB8Y0ZFabxSWbWovY3uYSQ2pTgmZeNu2VS4cg", async () => {
  const tools = { publish_text: { method: "POST", path: "/1.1/statuses/update.json", fixed_params: { include_entities: "true" }, body_format: "form", body: { status: "text" }, result: { fields: { id: "id_str" } } } };
  const { client, log } = await wire(synth({ type: "none", fields: [], sign: { mode: "oauth1" } }, tools, "https://api.x.com", "social"),
    { consumer_key: "xvz1evFS4wEEPTGEFPHBog", consumer_secret: "kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw", access_token: "370773112-GmHxMAgYyLbNEtIKZeRNFsMKPR9EyMZeS9weJAEb", access_token_secret: "LswwdoUaIvS8ltyTt5jkRh4J50vUPVVHtR2YPi5kE" }, { id_str: "1" });
  assert.equal((await client.callTool({ name: "publish_text", arguments: { text: "Hello Ladies + Gentlemen, a signed OAuth request!" } })).isError, false);
  assert.equal(oauthHeader(log[0].init.headers.Authorization).oauth_signature, "Ls93hJiZbQ3akF3HF3x1Bz8/zU4=");
}));

for (const [symbol, sig] of [["LTCBTC", "c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71"], ["１２３４５６", "e1353ec6b14d888f1164ae9af8228a3dbd508bc82eb867db8ab6046442f33ef3"]]) {
  test(`Binance documented signature example (${symbol}) through the catalog auth block (wire)`, () => withClock(1499827319559, null, async () => {
    const e = entry("trading/binance_spot.json");
    const tools = { place_order: { ...e.adapter.tools.place_order, fixed_params: { recvWindow: "5000" } } };
    const { client, log } = await wire(synth(e.adapter.auth, tools, "https://api.binance.com", "trading"),
      { api_key: "vmPUZE6mv9SD5VNHk4HlWFsOr6aKE2zvsw0MuIgwCIPy6utIco14y7Ju91duEh8A", api_secret: "NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j" }, { orderId: 1, status: "NEW" });
    assert.equal((await client.callTool({ name: "place_order", arguments: { symbol, side: "buy", type: "limit", quantity: 1, price: 0.1 } })).isError, false);
    const q = log[0].url.split("?")[1];
    assert.ok(q.split("&signature=")[0].endsWith("&price=0.1&recvWindow=5000&timestamp=1499827319559"));
    assert.equal(q.split("&signature=")[1], sig);
  }));
}

test("Kaufland documented signature example through the catalog auth block (wire)", () => withClock(1411055926000, null, async () => {
  const e = entry("ecommerce_channels/kaufland.json");
  const creds = Object.fromEntries(e.adapter.auth.fields.map((f) => [f.name, "x".repeat(32)]));
  creds.secret_key = "a7d0cb1da1ddbc86c96ee5fedd341b7d8ebfbb2f5c83cfe0909f4e57f05dd403";
  const { client, log } = await wire(synth(e.adapter.auth, { me: { kind: "probe", method: "POST", path: "/v2/units/" } }, "https://sellerapi.kaufland.com"), creds);
  assert.equal((await client.callTool({ name: "me", arguments: {} })).isError, false);
  assert.equal(log[0].init.headers["Shop-Timestamp"], "1411055926");
  assert.equal(log[0].init.headers["Shop-Signature"], "da0b65f51c0716c1d3fa658b7eaf710583630a762a98c9af8e9b392bd9df2e2a");
}));

test("JWT HS256 published example (wire)", () => withClock(1516239022000, null, async () => {
  const auth = { type: "none", fields: [], sign: { mode: "jwt_hs256", key_field: "api_secret", claims: { sub: "1234567890", name: "John Doe", iat: "{timestamp_s}" }, headers: { Authorization: "Bearer {signature}" } } };
  const { client, log } = await wire(synth(auth, { me: { kind: "probe", path: "/me" } }, "https://api.vec.example"), { api_secret: "your-256-bit-secret" });
  assert.equal((await client.callTool({ name: "me", arguments: {} })).isError, false);
  assert.equal(log[0].init.headers.Authorization, "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c");
}));

// ---- catalog fixes found by the audit
for (const [since, sent] of [["2026-09-01", "2026-09-01T00:00:00.000Z"], ["2026-09-01T10:30:00+02:00", "2026-09-01T08:30:00.000Z"]]) {
  test(`wix_stores list_orders sends an ISO dateTime filter (${since}) (wire)`, async () => {
    const { client, log } = await wire(entry("ecommerce_channels/wix_stores.json"), { api_key: "k".repeat(12), site_id: "s".repeat(12) }, { orders: [] });
    assert.equal((await client.callTool({ name: "list_orders", arguments: { since } })).isError, false);
    assert.equal(JSON.parse(log[0].init.body).search.filter.createdDate.$gte, sent);
  });
}

test("xiaomi_getapps_ads me probes countryList (campaign/list needs accountIds) (wire)", async () => {
  const { client, log } = await wire(entry("ads/xiaomi_getapps_ads.json"), { app_id: "a".repeat(8), app_key: "k".repeat(8) },
    (url) => (url.includes("createToken") ? { code: 0, result: { accessToken: "TOKEN-mi" } } : { code: 0, result: [{ geoType: "COUNTRY", id: "AF", name: "Afghanistan" }] }));
  assert.equal((await client.callTool({ name: "me", arguments: {} })).isError, false);
  assert.equal(log[1].url, "https://global.e.mi.com/foreign/marketing/region/countryList");
});

test("freelancehunt submit_bid is not offered (410 after the v2 deprecation)", () => {
  const a = entry("deals/freelancehunt.json").adapter;
  assert.equal(a.tools.submit_bid, undefined);
  assert.match(a.not_offered.submit_bid, /410/);
});

for (const [rel, verb, args, body] of [
  ["ads/tiktok.json", "list_accounts", {}, { code: 40105, message: "Access token is incorrect or has been revoked.", request_id: "x" }],
  ["marketplaces/digistore24.json", "list_products", {}, { api_version: "1.2", result: "error", message: "The API key is invalid.", code: 0 }],
  ["jobs/saramin.json", "search", { query: "python" }, { code: 2, message: "사용 불가능한 access-key 입니다. " }],
  ["ads/baidu_marketing.json", "list_campaigns", { account_id: "1" }, { header: { desc: "failure", failures: [{ code: 89406, position: "_user", message: "The access token you provided is invalidate." }], oprs: 0, succ: 0 } }],
]) {
  test(`${rel}: an error body in a 200 is an isError result, not an empty success (wire)`, async () => {
    const e = entry(rel);
    const creds = Object.fromEntries([...(e.adapter.auth.fields ?? []).map((f) => [f.name, "x".repeat(12)]), ...(e.adapter.config_fields ?? []).map((f) => [f.name, "1234567"])]);
    const tokenUrl = e.adapter.auth.token_url; // a valid token, so the error comes from the API call itself
    const { client } = await wire(e, creds, (url) => (tokenUrl && url.startsWith(tokenUrl) ? { code: 0, data: { accessToken: "ACCESS-x", refreshToken: "REFRESH-x", expiresIn: 86400 } } : body));
    const res = await client.callTool({ name: verb, arguments: args });
    assert.equal(res.isError, true, JSON.stringify(res.structuredContent));
    assert.ok(["auth_error", "upstream_error"].includes(res.structuredContent.error));
  });
}
