import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../runtime/typescript/dist/index.js";

const SPEC = JSON.parse(readFileSync(new URL("../catalog/market_data/ecb_data_portal.json", import.meta.url), "utf8"));
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

const XML = readFileSync(new URL("./fixtures/live/ecb_exr_usd.xml", import.meta.url), "utf8");

test("ecb_data_portal get_series asks for SDMX generic XML and parses it (wire)", async () => {
  const { client, log } = await connect({}, () => ({ body: XML, type: "application/vnd.sdmx.genericdata+xml;version=2.1" }));
  const r = (await client.callTool({ name: "get_series", arguments: { series_id: "EXR/D.USD.EUR.SP00.A", start: "2026-09-01", end: "2026-09-04" } })).structuredContent;
  assert.deepEqual(r.points.map((p) => [p.time, p.value]), [["2026-09-01", 1.159], ["2026-09-02", 1.1578], ["2026-09-03", 1.1615], ["2026-09-04", 1.1622]]);
  assert.equal(log[0].url.pathname, "/service/data/EXR/D.USD.EUR.SP00.A");
  assert.equal(hdr(log[0].init, "Accept"), "application/vnd.sdmx.genericdata+xml;version=2.1");
});
