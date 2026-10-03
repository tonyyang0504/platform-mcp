import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/ads/yahoo_dsp.json", import.meta.url), "utf8"));
const CREDS = { client_id: "197031e8-1546-410f", client_secret: "SECRET-yahoo-dsp-0123456789abcdef0123" };
const jsonResp = (status, body) => ({ status, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null) }, text: async () => JSON.stringify(body) });

async function connect(log, handler) {
  const f = async (url, init) => { log.push({ url, init }); return url.startsWith("https://id.b2b.yahooincapis.com") ? jsonResp(200, { access_token: "3f94eb47-a295", expires_in: "599" }) : handler(url, init); };
  for (const [k, v] of Object.entries(CREDS)) process.env[`PLATFORM_MCP_YAHOO_DSP_${k.toUpperCase()}`] = v;
  const server = buildServer(SPEC, undefined, f);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("yahoo_dsp: HS256 client assertion, X-Auth headers and campaign pause (wire)", async () => {
  const log = [];
  const c = await connect(log, (url) => jsonResp(200, { response: { id: 745085, status: "PAUSED" }, errors: null }));
  const res = await c.callTool({ name: "pause_resume", arguments: { campaign_id: "745085", action: "pause" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "PAUSED");
  const form = new URLSearchParams(log[0].init.body);
  assert.equal(form.get("realm"), "dsp"); assert.equal(form.get("scope"), "api-client"); assert.equal(form.get("client_secret"), null); assert.equal(form.get("client_id"), null);
  const [h, p, s] = form.get("client_assertion").split(".");
  assert.equal(crypto.createHmac("sha256", CREDS.client_secret).update(`${h}.${p}`).digest("base64url"), s);
  const claims = JSON.parse(Buffer.from(p, "base64url"));
  assert.equal(claims.iss, "idb2b.dsp.dspapi.197031e8-1546-410f"); assert.equal(claims.aud, "https://id.b2b.yahooincapis.com/zts/v1");
  assert.equal(log[1].url, "https://dspapi.admanagerplus.yahoo.com/traffic/campaigns/745085");
  assert.equal(log[1].init.method, "PUT");
  assert.equal(log[1].init.headers["X-Auth-Token"], "3f94eb47-a295"); assert.equal(log[1].init.headers["X-Auth-Method"], "OAuth2");
  assert.deepEqual(JSON.parse(log[1].init.body), { status: "PAUSED" });
});
