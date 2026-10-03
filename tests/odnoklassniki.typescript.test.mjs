import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => ({ "content-type": "application/json" })[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/social/odnoklassniki.json", import.meta.url), "utf8"));
const CREDS = { application_key: "CBAKEYOK123", application_secret_key: "OKSECRET-0123456789", access_token: "tkn-ok-abcdef0123", group_id: "53038939046008" };

async function connect(handler) {
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", fakeFetch(handler), a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

function check(url, init) {
  const q = Object.fromEntries(url.searchParams); const sig = q.sig; delete q.sig;
  assert.equal(q.access_token, undefined);
  const ssk = crypto.createHash("md5").update(CREDS.access_token + CREDS.application_secret_key).digest("hex");
  assert.equal(sig, crypto.createHash("md5").update(Object.keys(q).sort().map((k) => `${k}=${q[k]}`).join("") + ssk).digest("hex"));
  assert.equal(new URLSearchParams(String(init.body)).get("access_token"), CREDS.access_token);
  return q;
}

test("odnoklassniki: publish_text is signed without access_token, token in the POST body (wire)", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: "155013581046904" }; });
  const res = await client.callTool({ name: "publish_text", arguments: { text: "Hello OK" } });
  assert.equal(res.isError, false);
  assert.equal(seen.init.method, "POST");
  const q = check(seen.url, seen.init);
  assert.equal(q.method, "mediatopic.post"); assert.equal(q.type, "GROUP_THEME"); assert.equal(q.gid, CREDS.group_id);
  assert.deepEqual(JSON.parse(q.attachment), { media: [{ type: "text", text: "Hello OK" }] });
});

test("odnoklassniki: me, delete and error bodies", async () => {
  const seen = [];
  const client = await connect((url, init) => { seen.push({ url, init }); const m = url.searchParams.get("method");
    if (m === "users.getCurrentUser") return { body: { uid: "574829" } };
    if (m === "mediatopic.deleteTopic") return { body: { restore_id: "R1", success: true } };
    return { body: { error_code: 100, error_msg: "PARAM : bad topic" } }; });
  assert.equal((await client.callTool({ name: "me", arguments: {} })).structuredContent.account.uid, "574829");
  const d = await client.callTool({ name: "delete", arguments: { post_id: "155" } });
  assert.equal(d.structuredContent.status, "deleted");
  assert.equal(check(seen[1].url, seen[1].init).delete_id, "155");
  const a = await client.callTool({ name: "analytics_post", arguments: { post_id: "155" } });
  assert.equal(a.isError, true);
});
