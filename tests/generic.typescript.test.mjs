// Generic entries (tools from the API's own operations), shared with tests/test_generic_python.py: identical answers.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { connect } from "./lib/harness.mjs";
import { validateEntry } from "../runtime/typescript/dist/index.js";

const FIX = JSON.parse(readFileSync(new URL("./fixtures/generic_cases.json", import.meta.url), "utf8"));
const get = (obj, path) => { for (const part of path.split(".")) { if (part === "length") return obj.length; obj = Array.isArray(obj) ? obj[Number(part)] : obj?.[part]; } return obj; };
const spec = (adapter) => ({ id: "generic_case", category: "generic", label: "Case", docs_url: "https://docs.example.test/", adapter });

for (const c of FIX.cases) {
  test(`generic case: ${c.name}`, async () => {
    let n = 0;
    const { call, log } = await connect(spec(c.adapter), (u) => {
      if (u.host !== "api.example.test") throw new Error(`request to ${u.host}`);
      const r = c.responses[Math.min(n++, c.responses.length - 1)];
      const headers = { ...(r.headers ?? {}) }; const type = headers["content-type"] ?? ("text" in r ? undefined : "application/json"); delete headers["content-type"];
      return { status: r.status, body: "text" in r ? (r.text === "" ? undefined : r.text) : r.body, type, headers };
    });
    const res = await call(c.verb, c.args);
    const out = res.structuredContent;
    if (c.error) { assert.equal(res.isError, true, JSON.stringify(out)); assert.equal(out.error, c.error.kind); }
    else assert.ok(!res.isError, JSON.stringify(out));
    for (const [path, want] of Object.entries(c.expect ?? {})) assert.deepEqual(get(out, path), want, path);
    const want = c.request ?? {};
    if ("count" in want) assert.equal(log.length, want.count);
    const last = log[log.length - 1];
    if (want.path) assert.equal(last.url.pathname, want.path);
    for (const [k, v] of Object.entries(want.query ?? {})) assert.equal(last.url.searchParams.get(k), v);
    if (want.body) assert.deepEqual(JSON.parse(last.init.body), want.body);
  });
}

test("generic tools carry their own titles, annotations and schemas", async () => {
  const { client } = await connect(spec(FIX.cases[0].adapter), () => ({}));
  const { tools } = await client.listTools();
  const byName = Object.fromEntries(tools.map((t) => [t.name, t]));
  assert.deepEqual(Object.keys(byName).sort(), Object.keys(FIX.tools).sort());
  for (const [name, want] of Object.entries(FIX.tools)) {
    const t = byName[name];
    assert.equal(t.title, want.title, name);
    assert.equal(t.annotations.readOnlyHint, want.read_only, name);
    assert.equal(t.annotations.destructiveHint, want.destructive, name);
    assert.deepEqual(t.inputSchema.required, want.required, name);
    assert.deepEqual(Object.keys(t.inputSchema.properties).sort(), want.properties, name);
    assert.equal(t.inputSchema.additionalProperties, false);
    assert.deepEqual(t.outputSchema.required, ["data"]);
  }
});

test("hostile generic text is cleaned before clients see it", async () => {
  const { client } = await connect(FIX.hostile, () => ({}));
  const t = (await client.listTools()).tools[0];
  assert.ok(!t.description.includes("Ignore previous") && t.description.includes("[removed]"));
  assert.ok(!JSON.stringify(t.inputSchema).includes("<system>") && !(t.title ?? "").includes("‮"));
});

test("serve --entry validation accepts generic entries", () => {
  const good = { id: "probe", category: "generic", version: "0.1.0", adapter: FIX.cases[0].adapter };
  assert.deepEqual(validateEntry(good), []);
  const bad = JSON.parse(JSON.stringify(good));
  bad.adapter.tools["Bad Name"] = bad.adapter.tools.get_item; delete bad.adapter.tools.get_item;
  assert.ok(validateEntry(bad).some((e) => e.includes("generic tools need a name")));
});
