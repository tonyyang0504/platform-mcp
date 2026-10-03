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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/builder_tools/seedance.json", import.meta.url), "utf8"));
Object.assign(process.env, {"PLATFORM_MCP_SEEDANCE_API_KEY": "ark-secret"});

test("seedance generate_video: content array body (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { id: "cgt-1" } }; });
  const res = await client.callTool({ name: "generate_video", arguments: { prompt: "kitten", model: "seedance-1-5-pro-251215", duration_seconds: 5 } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].url.href, "https://ark.ap-southeast.bytepluses.com/api/v3/contents/generations/tasks");
  assert.equal(seen[0].init.headers.Authorization, "Bearer ark-secret");
  assert.deepEqual(body(seen[0].init), { model: "seedance-1-5-pro-251215", content: [{ type: "text", text: "kitten" }], duration: 5 });
  assert.equal(res.structuredContent.job_id, "cgt-1");
});

test("seedance get_job: video_url of a finished task (wire)", async () => {
  const client = await connect(SPEC, () => ({ body: { id: "cgt-1", status: "succeeded", content: { video_url: "https://tos/v.mp4" } } }));
  const res = await client.callTool({ name: "get_job", arguments: { job_id: "cgt-1" } });
  assert.equal(res.structuredContent.output_url, "https://tos/v.mp4");
});
