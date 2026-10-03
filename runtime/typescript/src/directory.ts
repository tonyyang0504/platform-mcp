#!/usr/bin/env node
/** Directory MCP server (`platform-mcp-hub directory`): which platforms exist per category, which have an API,
 * which are served by platform-mcp-hub, what each can do, and how to run it. Same server as the Python runtime's
 * directory.py, over the same snapshot (catalog/directory.json). */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { McpServer } from "@modelcontextprotocol/server";
import { catalogDir, REPO_URL as REPO } from "./catalog.js";
import { VERSION } from "./version.js";

type Platform = Record<string, any>;
interface Directory { snapshot: { platforms: number; served: number }; platforms: Platform[]; categories: { category: string; platforms: number; served: number; api_platforms: number }[]; verbs: Record<string, Record<string, any>> }

let cached: Directory | undefined;
export function data(): Directory {
  if (!cached) cached = JSON.parse(readFileSync(join(catalogDir(), "directory.json"), "utf8")) as Directory;
  return cached;
}

function jsonSchema(schema: Record<string, unknown>) {
  return { "~standard": { version: 1 as const, vendor: "platform-mcp", validate: (value: unknown) => ({ value }), jsonSchema: { input: () => schema, output: () => schema } } };
}
const summary = (p: Platform) => Object.fromEntries(["id", "category", "label", "lane", "has_api", "served", "tools", "url", "docs_url", "regions"].map((k) => [k, p[k] ?? null]));
const result = (payload: Record<string, unknown>, isError = false) => ({ content: [{ type: "text" as const, text: JSON.stringify(payload) }], structuredContent: payload, isError });

const UNPUBLISHED = "Unpublished: platform-mcp-hub is not on PyPI or npm yet; run it from source (never `uvx`/`npx` the name before it is published: anyone could register it first).";

/** How to run one served platform. Identical to install_hints in directory.py. */
export function installHints(p: Platform): Record<string, unknown> {
  const env = Object.fromEntries((p.credentials ?? []).map((c: any) => [c.env, "<value>"]));
  const ref: string = p.serve ?? p.id;
  const hints: Record<string, unknown> = { env, serve: `platform-mcp-hub serve ${ref}` };
  if (!(data() as any).snapshot?.published) { // catalog/schema/release.json is false until the operator publishes (docs/RELEASE_CHECKLIST.md)
    hints.status = "unpublished";
    hints.warning = UNPUBLISHED;
    hints.from_source = {
      python: `uvx --from git+${REPO} platform-mcp-hub serve ${ref}`,
      checkout: `git clone ${REPO} && cd platform-mcp && uv run platform-mcp-hub serve ${ref}`,
      typescript: `cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve ${ref}`,
    };
  } else {
    hints.uvx = `uvx platform-mcp-hub serve ${ref}`;
    hints.npx = `npx -y platform-mcp-hub serve ${ref}`;
    hints.claude_code = `claude mcp add ${p.id} -- uvx platform-mcp-hub serve ${ref}`;
    hints.claude_desktop = { mcpServers: { [p.id]: { command: "uvx", args: ["platform-mcp-hub", "serve", ref], env } } };
  }
  hints.http = `platform-mcp-hub serve ${ref} --http --port 8000  # Streamable HTTP on http://127.0.0.1:8000/mcp`;
  hints.source = `${REPO}/blob/main/catalog/${p.category}/${p.id}.json`;
  return hints;
}

function matches(p: Platform, f: { category?: string; query?: string; served_only?: boolean; has_api?: boolean; region?: string }): boolean {
  if (f.category && p.category !== f.category) return false;
  if (f.served_only && !p.served) return false;
  if (f.has_api === true && p.has_api !== "yes") return false;
  if (f.has_api === false && p.has_api === "yes") return false;
  if (f.region && !(p.regions ?? []).map((r: any) => String(r).toLowerCase()).includes(f.region.toLowerCase())) return false;
  if (f.query) {
    const hay = (["id", "label", "url", "docs_url", "kind"].map((k) => String(p[k] ?? "")).join(" ") + " " + (p.capabilities ?? []).join(" ")).toLowerCase();
    return f.query.toLowerCase().split(/\s+/).every((tok) => hay.includes(tok));
  }
  return true;
}

export function buildServer(): McpServer {
  const d = data();
  const served = d.categories.reduce((n, c) => n + c.served, 0);
  const server = new McpServer({ name: "platform-mcp-hub-directory", title: "platform-mcp-hub directory", version: VERSION }, {
    instructions: `Directory of ${d.platforms.length} platforms in ${d.categories.length} categories (${d.categories.map((c) => c.category).join(", ")}); ${served} of them are served by platform-mcp-hub. Use list_categories to orient, list_platforms to browse or search, search_capabilities to find platforms that support a verb (e.g. \`search\`, \`publish_text\`, \`place_order\`), and describe_platform for the tool list, credential environment variables and install commands. Tools are read-only over a bundled snapshot.`,
  });
  const ro = { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false };
  const str = { type: "string" }, bool = { type: "boolean" }, int = { type: "integer", minimum: 0 };

  server.registerTool("list_categories", {
    title: "List categories",
    description: "Categories with platform counts, how many have a documented API and how many ship a ready MCP server, plus each category's shared verb vocabulary.",
    inputSchema: jsonSchema({ type: "object", properties: {}, additionalProperties: false }) as any,
    annotations: { title: "List categories", ...ro },
  }, async () => result({ categories: d.categories.map((c) => ({ ...c, verbs: Object.keys(d.verbs[c.category] ?? {}).sort() })), snapshot: d.snapshot }));

  server.registerTool("list_platforms", {
    title: "List or search platforms",
    description: "Browse or search platforms. Filter by category, free-text query (id, label, url, capabilities), served_only (ready MCP server), has_api, region; paginate with limit/offset.",
    inputSchema: jsonSchema({ type: "object", properties: { category: str, query: str, served_only: bool, has_api: bool, region: str, limit: int, offset: int }, additionalProperties: false }) as any,
    annotations: { title: "List or search platforms", ...ro },
  }, async (args: any = {}) => {
    const limit = Math.max(1, Math.min(Number(args.limit ?? 50), 200)), offset = Number(args.offset ?? 0);
    const rows = d.platforms.filter((p) => matches(p, args));
    return result({ total: rows.length, offset, limit, items: rows.slice(offset, offset + limit).map(summary) });
  });

  server.registerTool("describe_platform", {
    title: "Describe a platform",
    description: "Everything the directory knows about one platform: API facts, tools it offers (and the verbs it does not, with reasons), credential env vars, package names and install commands.",
    inputSchema: jsonSchema({ type: "object", properties: { platform_id: str }, required: ["platform_id"], additionalProperties: false }) as any,
    annotations: { title: "Describe a platform", ...ro },
  }, async (args: any) => {
    const p = d.platforms.find((x) => x.id === args?.platform_id);
    if (!p) return result({ error: "not_found", message: `no platform with id ${JSON.stringify(args?.platform_id)}; try list_platforms(query=...)` }, true);
    const out: Record<string, unknown> = { ...p, verbs: Object.fromEntries((p.tools ?? []).map((v: string) => [v, d.verbs[p.category]?.[v] ?? null])) };
    if (p.served) out.install = installHints(p);
    else out.how_to_add = `Not served yet. Author an adapter block for catalog/${p.category}/${p.id}.json (see ${REPO}/blob/main/docs/ADAPTER_CONTRACT.md).`;
    return result(out);
  });

  server.registerTool("search_capabilities", {
    title: "Search by capability",
    description: "Platforms that support a verb (a served tool name such as `search`, `publish_text`, `get_ticker`) or a catalogued capability keyword (e.g. `job_search`, `webhooks`).",
    inputSchema: jsonSchema({ type: "object", properties: { capability: str, category: str, served_only: bool, limit: int }, required: ["capability"], additionalProperties: false }) as any,
    annotations: { title: "Search by capability", ...ro },
  }, async (args: any) => {
    const cap = String(args.capability ?? "").toLowerCase().trim();
    const limit = Math.max(1, Math.min(Number(args.limit ?? 50), 200));
    const rows: Platform[] = [];
    for (const p of d.platforms) {
      if (args.category && p.category !== args.category) continue;
      if (args.served_only && !p.served) continue;
      const tools = (p.tools ?? []).map((t: string) => t.toLowerCase()), caps = (p.capabilities ?? []).map((c: string) => c.toLowerCase());
      if (tools.includes(cap) || caps.some((c: string) => c.includes(cap))) rows.push({ ...summary(p), matched: tools.includes(cap) ? "tool" : "capability" });
    }
    rows.sort((a, b) => Number(!a.served) - Number(!b.served) || String(a.category).localeCompare(b.category) || String(a.id).localeCompare(b.id));
    return result({ capability: args.capability, total: rows.length, items: rows.slice(0, limit) });
  });
  return server;
}

