import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: () => null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/deals/zbj.json", import.meta.url), "utf8"));
const CREDS = { app_key: "2016061718xxxxxx001", app_secret: "00A583ED7F8D", access_token: "d3aaf29a", openid: "94F0" };

async function connect(handler) {
  const server = buildServer(SPEC, new Transport(SPEC.adapter.base_url, SPEC.adapter.auth, CREDS, 50, "test", fakeFetch(handler), SPEC.adapter.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

test("zbj: SHA1 secret-wrapped signature over sorted params (wire)", async () => {
  let seen;
  const client = await connect((url) => { seen = url; return { body: { taskId: 144, title: "Logo", amount: 500, nickname: "boss" } }; });
  const res = await client.callTool({ name: "get_posting", arguments: { id: "144" } });
  assert.equal(res.isError, false);
  assert.equal(res.structuredContent.title, "Logo");
  const q = Object.fromEntries(seen.searchParams);
  const payload = CREDS.app_secret + Object.keys(q).filter((k) => k !== "sign").sort().map((k) => k + q[k]).join("") + CREDS.app_secret;
  assert.equal(q.sign, createHash("sha1").update(payload).digest("hex").toUpperCase());
  assert.equal(q.method, "zbj.task.getDetailById");
  assert.equal(q.appKey, CREDS.app_key);
});
