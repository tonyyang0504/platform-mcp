// The platform-mcp-hub CLI (TypeScript) and its parity with the Python CLI: the same list, the same describe for every
// served entry, and the same tools (names, titles, descriptions, annotations, input and output schemas) from
// `serve <id>` in both runtimes. tests/test_cli_python.py covers the Python side on its own.
import assert from "node:assert/strict";
import { spawnSync, spawn } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { Client, InMemoryTransport } from "../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, describe, iterEntries, VERSION } from "../runtime/typescript/dist/index.js";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const CLI = join(ROOT, "runtime", "typescript", "dist", "cli.js");
const PY = process.env.PYTHON ?? (existsSync(join(ROOT, ".venv", "bin", "python")) ? join(ROOT, ".venv", "bin", "python") : "python3");
const PYENV = { ...process.env, PYTHONPATH: join(ROOT, "runtime", "python") };
const node = (...args) => spawnSync(process.execPath, [CLI, ...args], { encoding: "utf8", timeout: 60000 });
const py = (...args) => spawnSync(PY, ["-m", "platform_mcp_hub", ...args], { encoding: "utf8", timeout: 120000, env: PYENV });

test("version is the npm package's and the Python package's", () => {
  const pkg = JSON.parse(readFileSync(join(ROOT, "runtime", "typescript", "package.json"), "utf8"));
  assert.equal(VERSION, pkg.version);
  assert.equal(node("--version").stdout.trim(), `platform-mcp-hub ${VERSION}`);
  assert.equal(py("--version").stdout.trim(), `platform-mcp-hub ${VERSION}`);
});

test("list --json is identical in both CLIs", () => {
  for (const args of [["list", "--json"], ["list", "--json", "--category", "trading"], ["list", "--json", "--query", "jobs remote"]]) {
    const a = node(...args), b = py(...args);
    assert.equal(a.status, 0, a.stderr); assert.equal(b.status, 0, b.stderr);
    assert.deepEqual(JSON.parse(a.stdout), JSON.parse(b.stdout), args.join(" "));
  }
});

test("errors are the same: ambiguous ids, unknown ids, bad entry files", () => {
  const dir = mkdtempSync(join(tmpdir(), "hub-cli-"));
  const bad = join(dir, "bad.json");
  writeFileSync(bad, JSON.stringify({ id: "x", category: "jobs", adapter: { base_url: "http://api.x.example", tools: { place_order: { path: "/s" } } } }));
  for (const args of [["describe", "linkedin"], ["describe", "no_such_platform"], ["serve", "../etc/passwd"], ["describe", "--entry", bad], ["frobnicate"]]) {
    const a = node(...args), b = py(...args);
    assert.equal(a.status, 2, args.join(" ")); assert.equal(b.status, 2, args.join(" "));
    assert.equal(a.stderr.trim(), b.stderr.trim(), args.join(" "));
  }
});

test("describe is identical for every served entry (credentials, run commands, registry names)", () => {
  const dump = spawnSync(PY, ["-c", "import json; from platform_mcp_hub import catalog; print(json.dumps({f\"{e['category']}/{e['id']}\": catalog.describe(e) for _, e in catalog.iter_entries(served_only=True)}))"], { encoding: "utf8", env: PYENV, maxBuffer: 1 << 28 });
  assert.equal(dump.status, 0, dump.stderr);
  const want = JSON.parse(dump.stdout);
  let n = 0;
  for (const [, e] of iterEntries(true)) { assert.deepEqual(describe(e), want[`${e.category}/${e.id}`], `${e.category}/${e.id}`); n++; }
  assert.equal(n, Object.keys(want).length); assert.ok(n > 400);
});

test("serve builds the same tools as the Python runtime for every served entry", async () => {
  const script = [
    "import asyncio, json", "from platform_mcp_hub import catalog", "from platform_mcp_hub.server import build_server",
    "async def main():",
    "    out = {}",
    "    for _, e in catalog.iter_entries(served_only=True):",
    "        tools = await build_server(e).list_tools()",
    "        out[f\"{e['category']}/{e['id']}\"] = [{'name': t.name, 'title': t.title, 'description': t.description, 'inputSchema': t.input_schema, 'outputSchema': t.output_schema,",
    "            'annotations': t.annotations.model_dump(by_alias=True, exclude_none=True), '_meta': t.meta} for t in tools]",
    "    print(json.dumps(out))",
    "asyncio.run(main())",
  ].join("\n");
  const dump = spawnSync(PY, ["-c", script], { encoding: "utf8", env: PYENV, maxBuffer: 1 << 28 });
  assert.equal(dump.status, 0, dump.stderr);
  const want = JSON.parse(dump.stdout);
  for (const [, e] of iterEntries(true)) {
    const server = buildServer(e);
    const [ct, st] = InMemoryTransport.createLinkedPair();
    await server.connect(st);
    const client = new Client({ name: "parity", version: "0" });
    await client.connect(ct);
    const { tools } = await client.listTools();
    const got = tools.map((t) => ({ name: t.name, title: t.title, description: t.description, inputSchema: t.inputSchema, outputSchema: t.outputSchema, annotations: t.annotations, _meta: t._meta }));
    const key = `${e.category}/${e.id}`;
    const strip = (rows) => rows.map(({ annotations, ...r }) => ({ ...r, annotations: Object.fromEntries(Object.entries(annotations ?? {}).filter(([k]) => k !== "title")) }));
    assert.deepEqual(strip(got), strip(want[key]), key);
    await client.close();
  }
});

test("generic entries: describe and the tools are identical in both runtimes", async () => {
  const FIX = JSON.parse(readFileSync(join(ROOT, "tests", "fixtures", "generic_cases.json"), "utf8"));
  const dir = mkdtempSync(join(tmpdir(), "hub-generic-"));
  const entries = [{ id: "probe_api", category: "generic", label: "Probe API", docs_url: "https://docs.example.test/", version: "0.1.0", adapter: FIX.cases[0].adapter }, FIX.hostile];
  for (const e of entries) {
    const file = join(dir, `${e.id}.json`);
    writeFileSync(file, JSON.stringify(e));
    const a = node("describe", "--entry", file), b = py("describe", "--entry", file);
    assert.equal(a.status, 0, a.stderr); assert.equal(b.status, 0, b.stderr);
    assert.deepEqual(JSON.parse(a.stdout), JSON.parse(b.stdout), e.id);
    const script = ["import asyncio, json, sys", "from platform_mcp_hub.server import build_server",
      "e = json.load(open(sys.argv[1]))",
      "tools = asyncio.run(build_server(e).list_tools())",
      "print(json.dumps([{'name': t.name, 'title': t.title, 'description': t.description, 'inputSchema': t.input_schema, 'outputSchema': t.output_schema, 'annotations': {k: v for k, v in t.annotations.model_dump(by_alias=True, exclude_none=True).items() if k != 'title'}, '_meta': t.meta} for t in tools]))"].join("\n");
    const dump = spawnSync(PY, ["-c", script, file], { encoding: "utf8", env: PYENV });
    assert.equal(dump.status, 0, dump.stderr);
    const server = buildServer(e);
    const [ct, st] = InMemoryTransport.createLinkedPair();
    await server.connect(st);
    const client = new Client({ name: "parity", version: "0" });
    await client.connect(ct);
    const got = (await client.listTools()).tools.map((t) => ({ name: t.name, title: t.title, description: t.description, inputSchema: t.inputSchema, outputSchema: t.outputSchema,
      annotations: Object.fromEntries(Object.entries(t.annotations ?? {}).filter(([k]) => k !== "title")), _meta: t._meta }));
    assert.deepEqual(got, JSON.parse(dump.stdout), e.id);
    await client.close();
  }
});

async function stdioTools(args) {
  const child = spawn(process.execPath, [CLI, ...args], { stdio: ["pipe", "pipe", "pipe"], env: { PATH: process.env.PATH } });
  const lines = [];
  let buf = "";
  child.stdout.on("data", (d) => { buf += d; let i; while ((i = buf.indexOf("\n")) >= 0) { lines.push(JSON.parse(buf.slice(0, i))); buf = buf.slice(i + 1); } });
  const send = (m) => child.stdin.write(JSON.stringify(m) + "\n");
  const wait = async (id) => { for (let i = 0; i < 200; i++) { const m = lines.find((l) => l.id === id); if (m) return m; await new Promise((r) => setTimeout(r, 50)); } throw new Error(`no answer to ${id}`); };
  send({ jsonrpc: "2.0", id: 1, method: "initialize", params: { protocolVersion: "2025-11-25", capabilities: {}, clientInfo: { name: "t", version: "0" } } });
  const init = await wait(1);
  send({ jsonrpc: "2.0", method: "notifications/initialized" });
  send({ jsonrpc: "2.0", id: 2, method: "tools/list" });
  const list = await wait(2);
  child.kill();
  return [init.result.serverInfo.name, list.result.tools.map((t) => t.name).sort()];
}

test("serve <id>, serve --entry and directory speak stdio", async () => {
  assert.deepEqual(await stdioTools(["serve", "reed"]), ["reed-mcp", ["get_posting", "me", "search"]]);
  const dir = mkdtempSync(join(tmpdir(), "hub-cli-"));
  const entry = JSON.parse(readFileSync(join(ROOT, "catalog", "jobs", "remotive.json"), "utf8"));
  entry.id = "my_board";
  writeFileSync(join(dir, "my_board.json"), JSON.stringify(entry));
  assert.deepEqual(await stdioTools(["serve", "--entry", join(dir, "my_board.json")]), ["my_board-mcp", Object.keys(entry.adapter.tools).sort()]);
  const [name, tools] = await stdioTools(["directory"]);
  assert.equal(name, "platform-mcp-hub-directory"); assert.equal(tools.length, 4);
});

test("HTTP mode keeps the bind policy", () => {
  const r = node("serve", "reed", "--http", "--host", "0.0.0.0");
  assert.equal(r.status, 2); assert.match(r.stderr, /refusing to serve HTTP/);
  const d = node("directory", "--http", "--host", "0.0.0.0", "--allow-remote");
  assert.equal(d.status, 2); assert.match(d.stderr, /PLATFORM_MCP_HTTP_TOKEN/);
});
