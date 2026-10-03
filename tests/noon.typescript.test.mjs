import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/noon.json", import.meta.url), "utf8"));
const { privateKey, publicKey } = crypto.generateKeyPairSync("rsa", { modulusLength: 2048 });
const CREDS = { key_id: "KEY-noon-1", private_key: privateKey.export({ type: "pkcs8", format: "pem" }), project_code: "PRJ123", warehouse_code: "WH-DXB-1", country_code: "ae" };
const jsonResp = (status, body) => ({ status, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null) }, text: async () => JSON.stringify(body) });

test("noon: RS256 JWT login body, all Set-Cookies replayed, stock update (wire)", async () => {
  const log = [];
  const f = async (url, init) => {
    log.push({ url, init });
    if (url.endsWith("/identity/public/v1/api/login")) return { status: 200, headers: { get: (k) => (k.toLowerCase() === "set-cookie" ? "_npsid=SESS-noon-1; Path=/; HttpOnly, _nprt=REFRESH-noon-1; Path=/" : "application/json") }, text: async () => "{}" };
    return jsonResp(200, { items: [{ partner_sku: "SKU-9", status: { status_code: "OK" } }] });
  };
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", f, a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const c = new Client({ name: "test", version: "0" });
  await c.connect(ct);
  const res = await c.callTool({ name: "set_inventory", arguments: { sku: "SKU-9", quantity: 7 } });
  assert.equal(res.isError, false);
  const login = JSON.parse(log[0].init.body);
  assert.equal(login.default_project_code, "PRJ123");
  const [h, p, s] = login.token.split(".");
  assert.ok(crypto.createVerify("RSA-SHA256").update(`${h}.${p}`).verify(publicKey, Buffer.from(s, "base64url")));
  assert.equal(JSON.parse(Buffer.from(p, "base64url")).sub, "KEY-noon-1");
  assert.equal(log[1].url, "https://noon-api-gateway.noon.partners/stock/v1/stock-update");
  assert.equal(log[1].init.headers.Cookie, "_npsid=SESS-noon-1; _nprt=REFRESH-noon-1");
  assert.deepEqual(JSON.parse(log[1].init.body), { items: [{ warehouse_code: "WH-DXB-1", partner_sku: "SKU-9", qty: 7 }] });
});
