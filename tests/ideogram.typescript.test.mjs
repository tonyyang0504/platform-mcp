import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer } from "../runtime/typescript/dist/index.js";

const fakeFetch = (handler) => async (url, init) => { const r = handler(new URL(url), init); return { status: r.status ?? 200, headers: { get: (k) => (r.headers ?? {})[k] ?? null }, text: async () => (r.raw ?? JSON.stringify(r.body ?? {})) }; };
async function connect(spec, handler) {
  globalThis.fetch = fakeFetch(handler);
  const server = buildServer(spec);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  return client;
}
const body = (init) => JSON.parse(init.body);

const SPEC = JSON.parse(readFileSync(new URL("../catalog/builder_tools/ideogram.json", import.meta.url), "utf8"));
Object.assign(process.env, {"PLATFORM_MCP_IDEOGRAM_API_KEY": "ideo-secret"});

test("ideogram generate_image: JSON image_request with Api-Key (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { data: [{ url: "https://i/x.png", seed: 3 }] } }; });
  const res = await client.callTool({ name: "generate_image", arguments: { prompt: "cat", aspect_ratio: "ASPECT_16_9", model: "V_2" } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].url.href, "https://api.ideogram.ai/generate");
  assert.equal(seen[0].init.headers["Api-Key"], "ideo-secret");
  assert.deepEqual(body(seen[0].init), { image_request: { prompt: "cat", aspect_ratio: "ASPECT_16_9", model: "V_2" } });
  assert.equal(res.structuredContent.output_url, "https://i/x.png");
});

test("ideogram get_job: GET /v1/generations/{id} (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { generation_id: "g1", status: "pending" } }; });
  const res = await client.callTool({ name: "get_job", arguments: { job_id: "g1" } });
  assert.equal(seen[0].url.pathname, "/v1/generations/g1");
  assert.equal(res.structuredContent.status, "pending");
});
