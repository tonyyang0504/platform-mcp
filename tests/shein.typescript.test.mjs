import assert from "node:assert/strict";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k.toLowerCase()] ?? null }, text: async () => JSON.stringify(r.body ?? {}) }; };
const SPEC = JSON.parse(readFileSync(new URL("../catalog/ecommerce_channels/shein.json", import.meta.url), "utf8"));
const CREDS = { open_key_id: "B96C15416C9240DF96BAA0BC9B367C6D", sign_key: "6BEC9C4B668B4B14B17EEF106BB98AE5test1", random_key: "test1", site: "shein-us", currency: "USD" };

async function connect(handler, spec = SPEC) {
  const a = spec.adapter;
  const server = buildServer(spec, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", fakeFetch(handler), a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}

const hdr = (init, name) => { const h = init.headers ?? {}; const k = Object.keys(h).find((x) => x.toLowerCase() === name.toLowerCase()); return k ? h[k] : undefined; };

test("shein: runtime reproduces the documented signature", async () => {
  const realNow = Date.now; Date.now = () => 1740709414000;
  try {
    const spec = JSON.parse(JSON.stringify(SPEC)); spec.adapter.tools.me.path = "/open-api/order/purchase-order-info";
    let seen;
    const client = await connect((url, init) => { seen = init; return { body: { code: "0", msg: "OK", info: {} } }; }, spec);
    const res = await client.callTool({ name: "me", arguments: {} });
    assert.equal(res.isError, false);
    assert.equal(hdr(seen, "x-lt-timestamp"), "1740709414000");
    assert.equal(hdr(seen, "x-lt-signature"), "test1ZDZjYTJjNzg5ZjUzMDdkZTU2N2Y3NzcxN2ZjZjA5OGIxMTRhZWI0MTU1MzQxNjZlNjFkMGQxOTJiYTk1YWNjYQ==");
  } finally { Date.now = realNow; }
});

test("shein: end_listing signs the shelf call", async () => {
  let seen;
  const client = await connect((url, init) => { seen = { url, init }; return { body: { code: "0", msg: "OK", info: { success_count: 1, failure_count: 0 } } }; });
  const res = await client.callTool({ name: "end_listing", arguments: { listing_id: "sMM23072039123259" } });
  assert.equal(res.isError, false);
  const ts = hdr(seen.init, "x-lt-timestamp");
  const hex = crypto.createHmac("sha256", CREDS.sign_key).update(`${CREDS.open_key_id}&${ts}&/open-api/goods/modify-skc-shelf`).digest("hex");
  assert.equal(hdr(seen.init, "x-lt-signature"), "test1" + Buffer.from(hex).toString("base64"));
  assert.deepEqual(JSON.parse(seen.init.body), { skc_site_info_list: [{ shelf_state: 2, site_list: ["shein-us"], skc_name: "sMM23072039123259" }] });
});

test("shein: non-zero code is an error result", async () => {
  const client = await connect(() => ({ body: { code: "10010", msg: "signature error" } }));
  const res = await client.callTool({ name: "me", arguments: {} });
  assert.equal(res.isError, true);
});
