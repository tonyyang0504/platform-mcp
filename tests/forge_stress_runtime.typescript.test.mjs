// Runtime regression cases from the forge stress test (2026-10), shared with tests/test_forge_stress_runtime_python.py.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { connect } from "./lib/harness.mjs";

const CASES = JSON.parse(readFileSync(new URL("./fixtures/forge_stress_cases.json", import.meta.url), "utf8"));
const get = (obj, path) => { for (const part of path.split(".")) { if (part === "length") return obj.length; obj = Array.isArray(obj) ? obj[Number(part)] : obj?.[part]; } return obj; };

for (const c of CASES) {
  test(`forge stress case: ${c.name}`, async () => {
    const spec = { id: "stress_case", category: c.category, label: "case", adapter: c.adapter };
    let n = 0;
    const { call, log } = await connect(spec, (u) => {
      if (u.host !== "api.example.test") throw new Error(`request to ${u.host}`);
      const r = c.responses[Math.min(n++, c.responses.length - 1)];
      const headers = { ...(r.headers ?? {}) }; const type = headers["content-type"]; delete headers["content-type"];
      if (r.bytes_b64) return { status: r.status, bytes: Buffer.from(r.bytes_b64, "base64"), type, headers };
      return { status: r.status, body: "text" in r ? r.text : r.body, type, headers };
    });
    const res = await call(c.verb, c.args);
    const out = res.structuredContent;
    if (c.error) {
      assert.equal(res.isError, true, JSON.stringify(out));
      assert.equal(out.error, c.error.kind, JSON.stringify(out));
      if (c.error.message !== undefined) assert.equal(out.message, c.error.message);
      if (c.error.contains !== undefined) assert.ok(out.message.includes(c.error.contains), out.message);
    } else assert.ok(!res.isError, JSON.stringify(out));
    for (const [path, want] of Object.entries(c.expect ?? {})) assert.deepEqual(get(out, path), want, path);
    const want = c.request ?? {};
    if ("count" in want) assert.equal(log.length, want.count);
    if (want.path || want.query) {
      const last = log[log.length - 1].url;
      if (want.path) assert.equal(last.pathname, want.path);
      for (const [k, v] of Object.entries(want.query ?? {})) assert.equal(last.searchParams.get(k), v);
    }
  });
}
