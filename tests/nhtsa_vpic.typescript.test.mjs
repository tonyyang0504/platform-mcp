import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/automotive/nhtsa_vpic.json", import.meta.url), "utf8"));
const resp = (status, body, type = "application/json") => ({ status, headers: { get: (k) => (k.toLowerCase() === "content-type" && body !== undefined ? type : null) }, text: async () => (body === undefined ? "" : typeof body === "string" ? body : JSON.stringify(body)) });

async function connect(creds, handler) {
  const log = [];
  const fetcher = async (url, init) => { log.push({ url: new URL(url), init }); const r = handler(new URL(url), init, log.length); return resp(r.status ?? 200, r.body, r.type); };
  const a = SPEC.adapter;
  const server = buildServer(SPEC, new Transport(a.base_url, a.auth, { ...creds }, 50, "test", fetcher, a.envelope ?? {}));
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return { client, log };
}
const hdr = (init, name) => { const h = init.headers ?? {}; const k = Object.keys(h).find((x) => x.toLowerCase() === name.toLowerCase()); return k ? h[k] : undefined; };

test("nhtsa_vpic decode_vin maps the flat record and fails cleanly on an undecodable VIN (wire)", async () => {
  const { client, log } = await connect({}, (u) => (u.pathname.endsWith("/1HGCM82633A004352")
    ? { body: { Count: 1, Results: [{ VIN: "1HGCM82633A004352", Make: "HONDA", Model: "Accord", ModelYear: "2003", Trim: "EX-V6", BodyClass: "Coupe", EngineModel: "J30A4", FuelTypePrimary: "Gasoline", ErrorCode: "0" }] } }
    : { body: { Count: 1, Results: [{ VIN: "zz-bad", Make: "", ModelYear: "", ErrorCode: "6,400", ErrorText: "6 - Incomplete VIN; 400 - Invalid Characters Present" }] } }));
  const ok = (await client.callTool({ name: "decode_vin", arguments: { vin: "1HGCM82633A004352" } })).structuredContent;
  assert.deepEqual([ok.vin, ok.make, ok.model, ok.year, ok.body, ok.engine, ok.fuel], ["1HGCM82633A004352", "HONDA", "Accord", 2003, "Coupe", "J30A4", "Gasoline"]);
  assert.equal(log[0].url.searchParams.get("format"), "json");
  const bad = await client.callTool({ name: "decode_vin", arguments: { vin: "zz-bad" } });
  assert.equal(bad.isError, true);
  assert.match(bad.structuredContent.message, /^6 - Incomplete VIN/);
});
