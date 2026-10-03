import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => ({ "content-type": "application/json" })[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/messaging/ses.json", import.meta.url), "utf8"));
const CREDS = { access_key_id: "AKIDSESEXAMPLE", secret_access_key: "sesSecretKey/EXAMPLE+0123456789", region: "eu-west-1", from_address: "shop@example.com" };
const HOST = "email.eu-west-1.amazonaws.com";

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", fakeFetch(handler), a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

function expectedAuth(method, path, body, amzDate) {
  const h = (x) => crypto.createHash("sha256").update(x).digest("hex");
  const canonical = [method, path, "", `host:${HOST}\nx-amz-date:${amzDate}\n`, "host;x-amz-date", h(body)].join("\n");
  const scope = `${amzDate.slice(0, 8)}/eu-west-1/ses/aws4_request`;
  const toSign = ["AWS4-HMAC-SHA256", amzDate, scope, h(canonical)].join("\n");
  let k = Buffer.from("AWS4" + CREDS.secret_access_key);
  for (const p of [amzDate.slice(0, 8), "eu-west-1", "ses", "aws4_request"]) k = crypto.createHmac("sha256", k).update(p).digest();
  return `AWS4-HMAC-SHA256 Credential=${CREDS.access_key_id}/${scope}, SignedHeaders=host;x-amz-date, Signature=${crypto.createHmac("sha256", k).update(toSign).digest("hex")}`;
}

test("ses: SendEmail is SigV4-signed over the JSON body (wire)", async () => {
  const realNow = Date.now; Date.now = () => 1790301600000;
  try {
    let seen;
    const client = await connect((url, init) => { seen = { url, init }; return { body: { MessageId: "0102018f-abc" } }; });
    const res = await client.callTool({ name: "send", arguments: { to: "ann@example.org", text: "Shipped", subject: "Order 42" } });
    assert.equal(res.isError, false); assert.equal(res.structuredContent.message_id, "0102018f-abc");
    assert.equal(seen.url.host, HOST); assert.equal(seen.url.pathname, "/v2/email/outbound-emails");
    const body = JSON.parse(seen.init.body);
    assert.equal(body.FromEmailAddress, "shop@example.com"); assert.deepEqual(body.Destination.ToAddresses, ["ann@example.org"]); assert.equal(body.Content.Simple.Subject.Data, "Order 42");
    assert.equal(seen.init.headers["X-Amz-Date"], "20260925T020000Z");
    assert.equal(seen.init.headers.Authorization, expectedAuth("POST", "/v2/email/outbound-emails", seen.init.body, "20260925T020000Z"));
  } finally { Date.now = realNow; }
});

test("ses: GetAccount probe and a 403 auth error", async () => {
  let n = 0;
  const client = await connect(() => (++n === 1 ? { body: { SendingEnabled: true } } : { status: 403, body: { message: "signature does not match" } }));
  assert.equal((await client.callTool({ name: "me", arguments: {} })).structuredContent.account.SendingEnabled, true);
  const e = await client.callTool({ name: "me", arguments: {} });
  assert.equal(e.isError, true); assert.equal(e.structuredContent.error, "auth_error");
});
