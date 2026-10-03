import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/messaging/twitch.json", import.meta.url), "utf8"));
const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (r.status === 204 ? "" : JSON.stringify(r.body ?? {})) }; };

async function connect(handler) {
  const a = SPEC.adapter;
  const creds = { client_id: "twcid", client_secret: "tw-client-secret", refresh_token: "tw-refresh-1", sender_id: "123", broadcaster_id: "999" };
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, creds, 50, "test", fakeFetch(handler)));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("twitch messaging: send whispers from sender_id to the recipient (wire)", async () => {
  const seen = [];
  const client = await connect((url, init) => { seen.push({ url, init }); return url.host === "id.twitch.tv" ? { body: { access_token: "tw-access-0001", expires_in: 14000 } } : { status: 204 }; });
  const res = await client.callTool({ name: "send", arguments: { to: "456", text: "hello" } });
  assert.equal(res.isError, false);
  const w = seen.find((s) => s.url.pathname === "/helix/whispers");
  assert.equal(w.url.searchParams.get("from_user_id"), "123");
  assert.equal(w.url.searchParams.get("to_user_id"), "456");
  assert.deepEqual(JSON.parse(w.init.body), { message: "hello" });
  assert.equal(w.init.headers["Client-Id"], "twcid");
});
