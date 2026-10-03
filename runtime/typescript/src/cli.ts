#!/usr/bin/env node
/** platform-mcp-hub command line (TypeScript). The serving commands behave exactly like the Python CLI
 * (`uvx platform-mcp-hub ...`); the authoring tools (lint, try, smoke, verify) are in the Python package.
 *
 *   platform-mcp-hub list [--category C] [--query TEXT] [--json]
 *   platform-mcp-hub describe <id | category/id> [--category C] | --entry my_entry.json      (JSON)
 *   platform-mcp-hub serve <id | category/id> [--category C] | --entry my_entry.json  [--http [--host H] [--port N] [--allow-remote]]
 *   platform-mcp-hub directory [--http [--host H] [--port N] [--allow-remote]]
 */
import { resolve as resolvePath } from "node:path";
import { realpathSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { StdioServerTransport } from "@modelcontextprotocol/server/stdio";
import { describe, EntryError, find, iterEntries, loadEntryFile, serveRef, type Entry } from "./catalog.js";
import { buildServer as buildDirectory } from "./directory.js";
import { main as serveMain } from "./server.js";
import { VERSION } from "./version.js";

const USAGE = `platform-mcp-hub ${VERSION}

  platform-mcp-hub list [--category C] [--query TEXT] [--json]
  platform-mcp-hub describe <id | category/id> [--category C]      (JSON)
  platform-mcp-hub describe --entry my_entry.json
  platform-mcp-hub serve <id | category/id> [--category C] [--http [--host H] [--port N] [--allow-remote]]
  platform-mcp-hub serve --entry my_entry.json [--http ...]
  platform-mcp-hub directory [--http [--host H] [--port N] [--allow-remote]]

Authoring tools (lint, try, smoke, verify) are in the Python package: uvx platform-mcp-hub --help.
Credentials always come from PLATFORM_MCP_<ID>_<FIELD> environment variables; \`describe\` lists them.`;

function pop(argv: string[], flag: string): string | undefined {
  const i = argv.indexOf(flag);
  if (i < 0) return undefined;
  if (i + 1 >= argv.length) throw new EntryError(`${flag} needs a value`);
  const v = argv[i + 1];
  argv.splice(i, 2);
  return v;
}

function resolveEntry(argv: string[]): [string, Entry] {
  const entry = pop(argv, "--entry");
  const category = pop(argv, "--category");
  if (entry) { const p = resolvePath(entry); return [p, loadEntryFile(p)]; }
  const ref = argv.find((a) => !a.startsWith("-"));
  if (!ref) throw new EntryError("name a platform (`platform-mcp-hub list`) or pass --entry <file.json>");
  argv.splice(argv.indexOf(ref), 1);
  return find(ref, category);
}

function listRows(category?: string, query?: string): Record<string, unknown>[] {
  const q = (query ?? "").toLowerCase().split(/\s+/).filter(Boolean);
  const rows: Record<string, unknown>[] = [];
  for (const [, e] of iterEntries(true)) {
    if (category && e.category !== category) continue;
    const hay = ["id", "label", "category", "docs_url", "url"].map((k) => String(e[k] ?? "")).join(" ").toLowerCase();
    if (q.length && !q.every((t) => hay.includes(t))) continue;
    rows.push({ id: e.id, category: e.category, label: e.label || e.id, serve: serveRef(e.id, e.category), tools: Object.keys(e.adapter.tools), auth: (e.adapter.auth ?? {}).type ?? "none" });
  }
  return rows;
}

const fail = (msg: string, code = 2): number => { console.error(`platform-mcp-hub: ${msg}`); return code; };

export async function run(argvIn: string[] = process.argv.slice(2)): Promise<number> {
  const argv = [...argvIn];
  if (!argv.length || ["-h", "--help", "help"].includes(argv[0])) { console.log(USAGE); return argv.length ? 0 : 2; }
  if (["-V", "--version", "version"].includes(argv[0])) { console.log(`platform-mcp-hub ${VERSION}`); return 0; }
  const [cmd, ...rest] = argv;
  try {
    if (cmd === "list") {
      const asJson = rest.includes("--json");
      const args = rest.filter((a) => a !== "--json");
      const category = pop(args, "--category"), query = pop(args, "--query");
      if (args.length) return fail(`unexpected arguments: ${args.join(" ")}`);
      const rows = listRows(category, query);
      if (asJson) { console.log(JSON.stringify({ total: rows.length, items: rows })); return 0; }
      const width = Math.max(10, ...rows.map((r) => String(r.serve).length));
      for (const r of rows) console.log(`${String(r.serve).padEnd(width)}  ${String(r.category).padEnd(20)} ${String(r.label).slice(0, 40).padEnd(40)}  ${(r.tools as string[]).join(", ")}`);
      console.error(`${rows.length} served platforms; \`platform-mcp-hub describe <id>\` for credentials and run commands`);
      return 0;
    }
    if (cmd === "describe") {
      const [, entry] = resolveEntry(rest);
      if (rest.length) return fail(`unexpected arguments: ${rest.join(" ")}`);
      console.log(JSON.stringify(describe(entry), null, 1));
      return 0;
    }
    if (cmd === "serve") {
      const [, entry] = resolveEntry(rest);
      await serveMain(entry as any, rest);
      return -1; // keep running (stdio or HTTP)
    }
    if (cmd === "directory") {
      if (rest.includes("--http")) {
        const { serveHttp, httpAuthToken } = await import("./http_server.js");
        const host = pop(rest, "--host") ?? "127.0.0.1";
        let token: string | undefined;
        try { token = httpAuthToken(host, rest.includes("--allow-remote")); } catch (e) { return fail((e as Error).message); }
        await serveHttp(buildDirectory, host, Number(pop(rest, "--port") ?? 8000), "/mcp", token);
      } else await buildDirectory().connect(new StdioServerTransport());
      return -1;
    }
    if (["lint", "try", "smoke", "verify"].includes(cmd)) return fail(`${cmd} is in the Python package: uvx platform-mcp-hub ${cmd} ...`);
  } catch (e) {
    if (e instanceof EntryError) return fail(e.message);
    throw e;
  }
  return fail(`unknown command ${JSON.stringify(cmd)}; run \`platform-mcp-hub --help\``);
}

const invoked = process.argv[1] ? (() => { try { return realpathSync(process.argv[1]); } catch { return process.argv[1]; } })() : "";
if (invoked && invoked === fileURLToPath(import.meta.url)) {
  // exitCode, not exit(): a large `list --json` written to a pipe must be flushed before the process ends
  run().then((code) => { if (code >= 0) process.exitCode = code; }).catch((e) => { console.error(e); process.exit(1); });
}
