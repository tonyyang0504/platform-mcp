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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/builder_tools/bfl.json", import.meta.url), "utf8"));
Object.assign(process.env, {"PLATFORM_MCP_BFL_API_KEY": "bfl-key-secret"});

test("bfl generate_image: POST /v1/{model} with x-key and Kontext body (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { id: "t1", polling_url: "https://api.us1.bfl.ai/v1/get_result?id=t1" } }; });
  const res = await client.callTool({ name: "generate_image", arguments: { prompt: "a red fox", aspect_ratio: "16:9", seed: 7 } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].url.href, "https://api.bfl.ai/v1/flux-kontext-pro");
  assert.equal(seen[0].init.headers["x-key"], "bfl-key-secret");
  assert.deepEqual(body(seen[0].init), { prompt: "a red fox", seed: 7, aspect_ratio: "16:9" });
  assert.equal(res.structuredContent.job_id, "t1");
});

test("bfl generate_video: t2v body with integer duration (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { id: "v1", polling_url: "https://x" } }; });
  await client.callTool({ name: "generate_video", arguments: { prompt: "waves", duration_seconds: 8 } });
  assert.equal(seen[0].url.pathname, "/v1/flux-3-video");
  assert.deepEqual(body(seen[0].init), { mode: "t2v", prompt: "waves", duration: 8 });
});
