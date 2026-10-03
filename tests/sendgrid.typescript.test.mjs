import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/messaging/sendgrid.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (r.text ?? JSON.stringify(r.body ?? {})) }; };

async function connect(handler) {
  // `sender` is the non-secret per-install config field used as from.email
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, { api_key: "SG.secret-key", sender: "sender@example.com" }, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("sendgrid: tools follow the messaging vocabulary (wire)", async () => {
  const { tools } = await (await connect(() => ({}))).listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["me", "send"]);
  const send = tools.find((t) => t.name === "send");
  assert.equal(send.annotations.readOnlyHint, false);
  assert.equal(send.annotations.destructiveHint, false);
  assert.deepEqual(send.inputSchema.required, ["to", "text"]);
  assert.equal(send._meta["platform_mcp/endpoint"], "/mail/send");
  assert.deepEqual(Object.keys(SPEC.adapter.not_offered).sort(), ["get_thread", "list_inbound", "mark_read", "reply"]);
});

test("sendgrid: send builds the personalizations / content arrays and accepts the empty 202 (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { status: 202, text: "", headers: { "X-Message-Id": "W0H2aKW7QIeoGqmmQ7bzXQ" } }; });
  const res = await client.callTool({ name: "send", arguments: { to: "receiver@example.com", subject: "Hello", text: "hi there" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.status, "accepted");
  assert.equal(seen.url.href, "https://api.sendgrid.com/v3/mail/send");
  assert.deepEqual(JSON.parse(seen.init.body), { personalizations: [{ to: [{ email: "receiver@example.com" }] }], from: { email: "sender@example.com" }, subject: "Hello", content: [{ type: "text/plain", value: "hi there" }] });
  assert.equal(seen.init.headers.Authorization, "Bearer SG.secret-key");
});

test("sendgrid: me reads the user account (wire)", async () => {
  const client = await connect(() => ({ body: { reputation: 100, type: "paid" } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, false);
  assert.deepEqual(res.structuredContent.account, { reputation: 100, type: "paid" });
});

test("sendgrid: 401 is an auth_error result that does not leak the key (wire)", async () => {
  const client = await connect(() => ({ status: 401, body: { errors: [{ message: "The provided authorization grant is invalid, expired, or revoked", field: null, help: null }] } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
  assert.equal(res.structuredContent.error, "auth_error");
  assert.ok(!JSON.stringify(res.structuredContent).includes("SG.secret-key"));
});
