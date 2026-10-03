import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/automotive/mercedes_benz_gebrauchtwagen.json", import.meta.url), "utf8"));
const CREDS = { api_key: "mb-key-0123456789abcdef", locale: "de_DE" };
const fakeFetch = (handler, seen) => async (url, init) => { const u = new URL(url); seen.push({ url: u, init }); const r = handler(u, init); return { status: r.status ?? 200, headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : null) }, text: async () => JSON.stringify(r.body ?? {}) }; };

async function connect(handler) {
  const a = SPEC.adapter;
  const seen = [];
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...CREDS }, 50, "test", fakeFetch(handler, seen), a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  client.seen = seen;
  return client;
}
const hdr = (init, name) => { const h = init.headers || {}; const k = Object.keys(h).find((x) => x.toLowerCase() === name.toLowerCase()); return k ? h[k] : undefined; };

test("mercedes_benz_gebrauchtwagen: decode_vin with x-api-key and locale (wire)", async () => {
  const client = await connect(() => ({ body: { vehicleData: { brand: { text: "Mercedes-Benz" }, modelName: "EQE", longType: "Mercedes-AMG EQE 43 4MATIC", body: { text: "Sports Tourer" }, enginetype: { text: "Elektroantrieb" }, fuel: { text: "Elektro" } } } }));
  const res = await client.callTool({ name: "decode_vin", arguments: { vin: "WDD2951321F999999" } });
  assert.equal(res.isError, false, JSON.stringify(res.structuredContent));
  assert.equal(res.structuredContent.make, "Mercedes-Benz"); assert.equal(res.structuredContent.trim, "Mercedes-AMG EQE 43 4MATIC");
  const s = client.seen[0];
  assert.equal(s.url.pathname, "/vehicle_specifications_fleet/v1/vehicles/WDD2951321F999999");
  assert.equal(s.url.searchParams.get("locale"), "de_DE"); assert.equal(hdr(s.init, "x-api-key"), "mb-key-0123456789abcdef");
});
