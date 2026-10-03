/** The catalog that ships with platform-mcp-hub (same rules as the Python runtime's catalog.py; the CLI parity
 * tests hold both to the same answers). Lookup order: PLATFORM_MCP_HUB_CATALOG, the copy packed into the npm
 * package (<package>/catalog), then the repository checkout (<repo>/catalog). */
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const PKG_DIR = resolve(dirname(fileURLToPath(import.meta.url)), ".."); // dist/.. = the package (runtime/typescript in a checkout)
const REPO_DIR = resolve(PKG_DIR, "..", "..");
export const NOT_CATEGORIES = ["schema", "sources"];
export const ID_RE = /^[a-z0-9_]{1,60}$/;
export const VERSION_RE = /^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$/;
export const CATALOG_ENV = "PLATFORM_MCP_HUB_CATALOG";
export const REPO_URL = "https://github.com/tonyyang0504/platform-mcp";
export const REGISTRY_PREFIX = "io.github.tonyyang0504";

export class EntryError extends Error {}
export type Entry = Record<string, any>;

const isCatalog = (p: string) => existsSync(join(p, "schema", "vocab.json"));

export function catalogDir(): string {
  const env = process.env[CATALOG_ENV];
  if (env) {
    if (!isCatalog(env)) throw new EntryError(`${CATALOG_ENV}=${env} is not a catalog directory (no schema/vocab.json)`);
    return resolve(env);
  }
  for (const p of [join(PKG_DIR, "catalog"), join(REPO_DIR, "catalog")]) if (isCatalog(p)) return p;
  throw new EntryError("no catalog found: reinstall platform-mcp-hub, or set PLATFORM_MCP_HUB_CATALOG to a checkout's catalog/ directory");
}

const vocabCache = new Map<string, Record<string, any>>();
export function vocab(): Record<string, any> {
  const p = join(catalogDir(), "schema", "vocab.json");
  if (!vocabCache.has(p)) vocabCache.set(p, JSON.parse(readFileSync(p, "utf8")));
  return vocabCache.get(p)!;
}

export function published(): boolean {
  try { return JSON.parse(readFileSync(join(catalogDir(), "schema", "release.json"), "utf8")).published === true; } catch { return false; }
}

const categories = (root: string) => readdirSync(root, { withFileTypes: true }).filter((d) => d.isDirectory() && !NOT_CATEGORIES.includes(d.name)).map((d) => d.name).sort();

/** Every entry file, sorted the way Python's sorted(glob("*\/*.json")) sorts them (by full path). */
export function entryFiles(root = catalogDir()): string[] {
  const out: string[] = [];
  for (const c of categories(root)) for (const f of readdirSync(join(root, c))) if (f.endsWith(".json")) out.push(join(root, c, f));
  return out.sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
}

export function* iterEntries(servedOnly = false, root = catalogDir()): Generator<[string, Entry]> {
  for (const p of entryFiles(root)) {
    let e: unknown;
    try { e = JSON.parse(readFileSync(p, "utf8")); } catch { continue; }
    if (!e || typeof e !== "object" || Array.isArray(e)) continue;
    if (servedOnly && !isObj((e as Entry).adapter)) continue;
    yield [p, e as Entry];
  }
}

const isObj = (v: unknown): v is Record<string, any> => !!v && typeof v === "object" && !Array.isArray(v);

export function servedCategories(pid: string, root = catalogDir()): string[] {
  const out: string[] = [];
  for (const c of categories(root)) {
    const p = join(root, c, `${pid}.json`);
    if (!existsSync(p)) continue;
    try { if (isObj(JSON.parse(readFileSync(p, "utf8")).adapter)) out.push(c); } catch { /* unreadable: not served */ }
  }
  return out;
}

export function find(refIn: string, categoryIn?: string): [string, Entry] {
  let ref = (refIn ?? "").trim(), category = categoryIn;
  if (ref.includes("/")) { const i = ref.indexOf("/"); category = ref.slice(0, i); ref = ref.slice(i + 1); }
  if (!ID_RE.test(ref) || (category !== undefined && (!ID_RE.test(category) || NOT_CATEGORIES.includes(category)))) {
    throw new EntryError(`not a platform id: ${JSON.stringify(ref)} (lowercase [a-z0-9_]; \`platform-mcp-hub list\` shows them)`);
  }
  const cats = servedCategories(ref);
  if (category) {
    if (!cats.includes(category)) throw new EntryError(`no served entry ${category}/${ref}` + (cats.length ? `; it is served in: ${cats.join(", ")}` : ""));
  } else if (!cats.length) {
    let n = 0; for (const _ of iterEntries(true)) n++;
    throw new EntryError(`no served entry ${JSON.stringify(ref)}; \`platform-mcp-hub list\` shows the ${n} served platforms`);
  } else if (cats.length > 1) {
    throw new EntryError(`${JSON.stringify(ref)} is served in several categories (${cats.join(", ")}): use <category>/${ref}, e.g. ${cats[0]}/${ref}`);
  } else category = cats[0];
  const p = join(catalogDir(), category!, `${ref}.json`);
  return [p, JSON.parse(readFileSync(p, "utf8"))];
}

/** The structural checks `serve --entry` makes before serving a file (identical to catalog.py validate_entry). */
export function validateEntry(entry: unknown): string[] {
  if (!isObj(entry)) return ["the entry must be a JSON object"];
  const errs: string[] = [];
  const { id: pid, category: cat } = entry;
  if (typeof pid !== "string" || !ID_RE.test(pid)) errs.push("id must match [a-z0-9_]{1,60}");
  const voc = vocab();
  const cats = Object.keys(voc).filter((k) => isObj(voc[k])).sort();
  const generic = cat === "generic";
  if (!generic && (typeof cat !== "string" || !cats.includes(cat))) errs.push(`category must be generic or one of: ${cats.join(", ")}`);
  const a = entry.adapter;
  if (!isObj(a)) { errs.push("no adapter block: only served entries (with `adapter`) can be served"); return errs; }
  if (typeof a.base_url !== "string" || !a.base_url.startsWith("https://")) errs.push("adapter.base_url must be an https URL");
  const tools = a.tools;
  if (!isObj(tools) || !Object.keys(tools).length) errs.push("adapter.tools must map at least one verb");
  else if (generic) {
    const bad = Object.entries(tools).filter(([n, t]) => !/^[a-z][a-z0-9_]{0,63}$/.test(n) || !isObj(t) || (t.input !== undefined && !isObj(t.input))).map(([n]) => n).sort();
    if (bad.length) errs.push(`generic tools need a name matching [a-z][a-z0-9_]{0,63} and an object input schema: ${bad.join(", ")}`);
  } else if (typeof cat === "string" && isObj(voc[cat])) {
    const unknown = Object.keys(tools).filter((v) => !(v in voc[cat])).sort();
    if (unknown.length) errs.push(`verbs not in the ${cat} vocabulary: ${unknown.join(", ")}`);
  }
  const version = entry.version ?? "0.1.0";
  if (typeof version !== "string" || !VERSION_RE.test(version)) errs.push("version must be MAJOR.MINOR.PATCH");
  return errs;
}

export function loadEntryFile(path: string): Entry {
  let entry: unknown;
  let text: string;
  try { text = readFileSync(path, "utf8"); } catch (e) { throw new EntryError(`cannot read ${path}: ${(e as NodeJS.ErrnoException).code ?? e}`); }
  try { entry = JSON.parse(text); } catch (e) { throw new EntryError(`${path} is not valid JSON: ${(e as Error).message}`); }
  const errs = validateEntry(entry);
  if (errs.length) throw new EntryError(`${path}: ` + errs.join("; "));
  return entry as Entry;
}

export const serveRef = (pid: string, category: string) => (servedCategories(pid).length > 1 ? `${category}/${pid}` : pid);
export const slug = (pid: string, category: string) => (servedCategories(pid).length > 1 ? `${pid}-${category.replace(/_/g, "-")}` : pid);
export const registryName = (pid: string, category: string) => `${REGISTRY_PREFIX}/${slug(pid, category)}-mcp`;

function where(e: Record<string, any>): string {
  if (e.base_url) return e.base_url;
  if (e.hosts) return "hosts " + Object.values(e.hosts).join(", ");
  if (e.same_host) return "production host with test accounts or test keys";
  return "production host with environment headers";
}

export function envVars(entry: Entry): Record<string, any>[] {
  const pid: string = entry.id, a = entry.adapter;
  const pre = `PLATFORM_MCP_${pid.toUpperCase()}_`;
  const out: Record<string, any>[] = [
    ...((a.auth ?? {}).fields ?? []).filter(isObj).map((f: any) => ({ name: pre + f.name.toUpperCase(), description: f.help ?? f.name, isRequired: f.required ?? true, isSecret: true })),
    ...(a.config_fields ?? []).filter(isObj).map((f: any) => ({ name: pre + f.name.toUpperCase(), description: f.help ?? f.name, isRequired: f.required ?? false, isSecret: false })),
  ];
  const envs = a.environments ?? {};
  const names = Object.keys(envs).sort();
  if (names.length) {
    const desc = "Vendor environment (default production): " + names.map((n) => `${n} = ${where(envs[n])}`).join("; ") + ". Credentials are the environment's own; see adapter.environments in the catalog entry.";
    out.push({ name: pre + "ENV", description: desc, isRequired: false, isSecret: false, default: "production", choices: ["production", ...names] });
    out.push({ name: pre + "BASE_URL", description: "Optional https base URL override (a mock or a private gateway); replaces the selected environment's base_url. Never echoed in errors.", isRequired: false, isSecret: false });
  }
  return out;
}

export function runCommands(pid: string, category: string): Record<string, string> {
  const ref = serveRef(pid, category);
  if (published()) {
    return { uvx: `uvx platform-mcp-hub serve ${ref}`, npx: `npx -y platform-mcp-hub serve ${ref}`,
             claude_code: `claude mcp add ${pid} -- uvx platform-mcp-hub serve ${ref}`, http: `uvx platform-mcp-hub serve ${ref} --http --port 8000` };
  }
  return { status: "unpublished",
           python: `uvx --from git+${REPO_URL} platform-mcp-hub serve ${ref}`,
           checkout: `git clone ${REPO_URL} && cd platform-mcp && uv run platform-mcp-hub serve ${ref}`,
           typescript: `cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve ${ref}`,
           http: `uv run platform-mcp-hub serve ${ref} --http --port 8000` };
}

export function describe(entry: Entry): Record<string, unknown> {
  const a = entry.adapter, pid: string = entry.id, cat: string = entry.category;
  return {
    id: pid, category: cat, label: entry.label || pid, version: entry.version ?? "0.1.0",
    docs_url: entry.docs_url ?? null, verified_at: entry.verified_at ?? null,
    tools: Object.fromEntries(Object.entries(a.tools).map(([v, t]: [string, any]) => [v, { method: t.method ?? "GET", path: t.path ?? null, docs: t.docs || entry.docs_url || null }])),
    not_offered: a.not_offered ?? {},
    auth: (a.auth ?? {}).type ?? "none",
    env: envVars(entry),
    live_check: entry.live_check ?? null,
    serve: serveRef(pid, cat), registry_name: registryName(pid, cat),
    run: runCommands(pid, cat),
  };
}
