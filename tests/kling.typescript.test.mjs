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

const SPEC = JSON.parse(readFileSync(new URL("../catalog/builder_tools/kling.json", import.meta.url), "utf8"));
Object.assign(process.env, {"PLATFORM_MCP_KLING_API_KEY": "kling-secret"});

test("kling generate_video: settings body, bearer key, envelope data (wire)", async () => {
  const seen = [];
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); return { body: { code: 0, message: "SUCCEED", data: { id: "t9", status: "submitted" } } }; });
  const res = await client.callTool({ name: "generate_video", arguments: { prompt: "a train", aspect_ratio: "9:16", duration_seconds: 10 } });
  assert.equal(res.isError, false);
  assert.equal(seen[0].url.href, "https://api-singapore.klingai.com/text-to-video/kling-3.0");
  assert.equal(seen[0].init.headers.Authorization, "Bearer kling-secret");
  assert.deepEqual(body(seen[0].init), { prompt: "a train", settings: { aspect_ratio: "9:16", duration: 10 } });
  assert.equal(res.structuredContent.job_id, "t9");
});

test("kling get_job: GET /tasks?task_ids and non-zero code is an error (wire)", async () => {
  const seen = [];
  let n = 0;
  const client = await connect(SPEC, (url, init) => { seen.push({ url, init }); n += 1; return n === 1 ? { body: { code: 0, data: [{ id: "t9", status: "succeeded", outputs: [{ type: "video", url: "https://v/1.mp4" }] }] } } : { body: { code: 1201, message: "task not found" } }; });
  const res = await client.callTool({ name: "get_job", arguments: { job_id: "t9" } });
  assert.equal(seen[0].url.searchParams.get("task_ids"), "t9");
  assert.equal(res.structuredContent.output_url, "https://v/1.mp4");
  const bad = await client.callTool({ name: "get_job", arguments: { job_id: "zz" } });
  assert.equal(bad.isError, true);
});
