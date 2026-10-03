import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/udbud_dk.json", import.meta.url), "utf8"));
const { privateKey, publicKey } = crypto.generateKeyPairSync("rsa", { modulusLength: 2048 });
const CREDS = { client_id: "udbud-client-7", private_key: privateKey.export({ type: "pkcs8", format: "pem" }), key_id: "kid-2026" };
const jsonResp = (status, body) => ({ status, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null) }, text: async () => JSON.stringify(body) });

test("udbud_dk: RS256 private_key_jwt assertion, then the DKUDBUD sync feed (wire)", async () => {
  const log = [];
  const f = async (url, init) => { log.push({ url, init }); return url.includes("openid-connect/token") ? jsonResp(200, { access_token: "ACCESS-ud-1", expires_in: 300 }) : jsonResp(200, { totalt: 1, bekendtgoerelser: [{ noticeId: "6a26cc22", noticeVersion: "01" }] }); };
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", f, a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const c = new Client({ name: "test", version: "0" });
  await c.connect(ct);
  const res = await c.callTool({ name: "search_postings", arguments: { limit: 5 } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.postings[0].id, "6a26cc22");
  const form = new URLSearchParams(log[0].init.body);
  assert.equal(form.get("client_id"), "udbud-client-7"); assert.equal(form.get("client_secret"), null);
  const [h, p, s] = form.get("client_assertion").split(".");
  assert.ok(crypto.createVerify("RSA-SHA256").update(`${h}.${p}`).verify(publicKey, Buffer.from(s, "base64url")));
  assert.equal(JSON.parse(Buffer.from(h, "base64url")).kid, "kid-2026");
  const claims = JSON.parse(Buffer.from(p, "base64url"));
  assert.equal(claims.aud, "https://auth.virk.dk/realms/erst/protocol/openid-connect/token"); assert.equal(claims.iss, "udbud-client-7");
  const u = new URL(log[1].url);
  assert.equal(u.pathname, "/udbud/ekstern-data/bekendtgoerelse/v1/fraKilde/DKUDBUD"); assert.equal(u.searchParams.get("size"), "5");
  assert.equal(log[1].init.headers.Authorization, "Bearer ACCESS-ud-1");
});
