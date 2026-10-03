import crypto from "node:crypto";
/** Declarative adapter interpreter with the same semantics as the Python runtime's adapter.py. */
import { InvalidInput, KINDS, NotFound, NotSupported, PlatformError, RATE_WORDS, RateLimited } from "./errors.js";
import { scrub } from "./credentials.js";
import { vocabFor } from "./vocab.js";
import { shape as genericShape } from "./generic.js";
import type { Transport } from "./http.js";

export interface ToolSpec { kind?: string; method?: string; path: string; params?: Record<string, unknown>; path_params?: Record<string, unknown>; fixed_params?: Record<string, unknown>; body?: Record<string, unknown>; result?: { items?: string; key?: string; total?: string; root?: string; fields?: Record<string, string> ; require?: string[] }; default_limit?: number; max_limit?: number; docs?: string; note?: string }
export interface Spec { id: string; category: string; label?: string; docs_url?: string; verified_at?: string; version?: string; instructions?: string; adapter: { base_url: string; auth?: any; rate_per_second?: number; tools: Record<string, ToolSpec>; not_offered?: Record<string, string> } }

export function dig(obj: unknown, path?: string | null): unknown {
  if (!path || path === "$") return obj;
  let cur: any = obj;
  for (const part of path.split(".")) {
    if (part === "*") { // the first value of an object keyed by a name the caller cannot know (Kraken), or the first array element
      if (cur && typeof cur === "object" && !Array.isArray(cur)) { const vals = Object.values(cur); cur = vals.length ? vals[0] : undefined; }
      else if (Array.isArray(cur)) cur = cur.length ? cur[0] : undefined;
      else return undefined;
    } else if (cur && typeof cur === "object" && !Array.isArray(cur)) cur = cur[part];
    else if (Array.isArray(cur) && /^\d+$/.test(part)) cur = cur[Number(part)];
    else return undefined;
  }
  return cur;
}

/** The page size a tool really uses: the `limit` argument (or default_limit), capped by max_limit. */
export function effectiveLimit(tool: ToolSpec, args: Record<string, unknown>): number {
  return Math.min(Number(args.limit || tool.default_limit || 25), Number(tool.max_limit ?? 100));
}
/** result.cap: head|tail — the platform ignores the page size: keep the first or the last `limit` rows. */
function applyCap<T>(items: T[], result: any, limit: number): T[] {
  if (result?.cap === "head") return items.slice(0, limit);
  if (result?.cap === "tail") return limit > 0 ? items.slice(-limit) : [];
  return items;
}

/** Split a dotted body key; a backslash-escaped dot (`m\\.relates_to`) stays inside the segment. */
function splitKey(key: string): string[] {
  return key.split(/(?<!\\)\./).map((seg) => seg.replace(/\\\./g, "."));
}

function setPath(root: any, parts: string[], value: unknown): void {
  let cur: any = root;
  for (let i = 0; i < parts.length - 1; i++) {
    const key: string | number = Array.isArray(cur) ? Number(parts[i]) : parts[i];
    if (cur[key] === undefined || cur[key] === null) cur[key] = /^\d+$/.test(parts[i + 1]) ? [] : {};
    cur = cur[key];
  }
  const last = parts[parts.length - 1];
  cur[Array.isArray(cur) ? Number(last) : last] = value;
}

function parseWhen(v: unknown): Date {
  if (typeof v === "number") return new Date(v * 1000);
  const t = String(v).trim();
  const d = /^\d{4}-\d{2}-\d{2}$/.test(t) ? new Date(`${t}T00:00:00Z`) : new Date(/[zZ]|[+-]\d{2}:?\d{2}$/.test(t) ? t : `${t}Z`);
  if (Number.isNaN(d.getTime())) throw new InvalidInput(`not an ISO date/datetime: ${JSON.stringify(v)}`);
  return d;
}
/** strftime restricted to %Y %y %m %d %H %M %S, identical to the Python runtime. */
function fmtWhen(pattern: string, d: Date): string {
  const p2 = (n: number) => String(n).padStart(2, "0");
  const map: Record<string, string> = { "%Y": String(d.getUTCFullYear()), "%y": p2(d.getUTCFullYear() % 100), "%m": p2(d.getUTCMonth() + 1), "%d": p2(d.getUTCDate()), "%H": p2(d.getUTCHours()), "%M": p2(d.getUTCMinutes()), "%S": p2(d.getUTCSeconds()) };
  return pattern.replace(/%[YymdHMS]/g, (t) => map[t]);
}
/** Exact decimal product rounded half-up to an integer (minor units, micros), identical to the Python runtime. */
function scaleInt(v: unknown, factor: string): number {
  const dec = (x: string): [bigint, number] => {
    const t = x.trim();
    if (!/^-?\d+(\.\d+)?$/.test(t)) throw new InvalidInput(`must be a number, got ${JSON.stringify(x)}`);
    const [ip, fp = ""] = t.split(".");
    return [BigInt(ip + fp), fp.length];
  };
  const [a, sa] = dec(String(v)); const [b, sb] = dec(factor);
  const prod = a * b; const scale = 10n ** BigInt(sa + sb);
  let q = prod / scale; const r = prod % scale; const neg = prod < 0n;
  if ((r < 0n ? -r : r) * 2n >= scale) q += neg ? -1n : 1n;
  return Number(q);
}

function epochIso(value: unknown): unknown {
  const num = typeof value === "number" ? value : typeof value === "string" && value.trim() !== "" && Number.isFinite(Number(value)) ? Number(value) : null;
  if (num === null) return value === undefined || value === "" ? null : value;
  const secs = Math.abs(num) >= 1e11 ? num / 1000 : num;
  return new Date(Math.floor(secs) * 1000).toISOString().replace(/\.\d{3}Z$/, "Z");
}

function toNumber(t: string): number | null { const n = t.trim() === "" ? NaN : Number(t); return Number.isFinite(n) ? n : null; }
/** Parse a value with a %d %m %Y %y %H %M %S pattern into ISO-8601 (same as adapter.py _iso_from_pattern). */
function isoFromPattern(pattern: string, value: unknown): unknown {
  if (typeof value !== "string" || !value.trim()) return value === undefined || value === "" ? null : value;
  let rx = ""; const order: string[] = [];
  for (let i = 0; i < pattern.length;) {
    const tok = pattern.slice(i, i + 2);
    if (["%Y", "%y", "%m", "%d", "%H", "%M", "%S", "%b", "%a"].includes(tok)) { rx += tok === "%Y" ? "(\\d{4})" : tok === "%b" || tok === "%a" ? "([A-Za-z]{3,9})" : "(\\d{1,2})"; order.push(tok); i += 2; } // %b month name, %a weekday (ignored)
    else { rx += pattern[i].replace(/[.*+?^${}()|[\]\\/]/g, "\\$&"); i += 1; }
  }
  const m = new RegExp(`^${rx}$`).exec(value.trim());
  if (!m) return value;
  const parts: Record<string, number> = {};
  for (let i = 0; i < order.length; i++) {
    const t = order[i]; const g = m[i + 1];
    if (t === "%a") continue;
    if (t === "%b") { const mo = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"].indexOf(g.slice(0, 3).toLowerCase()); if (mo < 0) return value; parts["%m"] = mo + 1; continue; }
    parts[t] = Number(g);
  }
  const p2 = (n: number) => String(n).padStart(2, "0");
  const year = "%Y" in parts ? parts["%Y"] : 2000 + (parts["%y"] ?? 0);
  const date = `${String(year).padStart(4, "0")}-${p2(parts["%m"] ?? 1)}-${p2(parts["%d"] ?? 1)}`;
  return ["%H", "%M", "%S"].some((t) => t in parts) ? `${date}T${p2(parts["%H"] ?? 0)}:${p2(parts["%M"] ?? 0)}:${p2(parts["%S"] ?? 0)}Z` : date;
}

function mapFields(record: unknown, fields: Record<string, string>, args: Record<string, unknown> = {}): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, rawSrc] of Object.entries(fields)) {
    let v: unknown;
    // a path segment named by an argument (Bank of Canada {"<series>": {"v": ...}} -> "num:{series_id}.v"); an absent argument leaves no path
    const src = !rawSrc.startsWith("=") && !rawSrc.startsWith("fmt:") && rawSrc.includes("{") ? rawSrc.replace(/\{([A-Za-z_][A-Za-z0-9_]*)\}/g, (_m, n) => (args[n] === undefined || args[n] === null || args[n] === "" ? "\u0000" : String(args[n]))) : rawSrc;
    if (src.startsWith("=")) v = src.slice(1);
    else if (src.startsWith("arg:")) { v = args[src.slice(4)]; if (v === "") v = null; } // arg:<name> — the value of a tool argument
    else if (src.startsWith("fmt:")) { // fmt:https://site/contest/{id} — a string built from record paths; null when any part is missing
      let missing = false;
      v = src.slice(4).replace(/\{([^{}]+)\}/g, (_m, path: string) => {
        const x = dig(record, path);
        if (x === undefined || x === null || x === "" || typeof x === "object") { missing = true; return ""; }
        return String(x);
      });
      if (missing) v = null;
    } else if (src.startsWith("isodate:")) { // isodate:<pattern>:<path> — a date in the platform's format as ISO (see adapter.py)
      const rest = src.slice(8); const cut = rest.includes("%") ? rest.indexOf(":", rest.lastIndexOf("%") + 2) : rest.indexOf(":");
      v = isoFromPattern(rest.slice(0, cut), dig(record, rest.slice(cut + 1)));
    } else if (src.startsWith("num_comma:")) { // num_comma:<path> — a decimal-comma number ("14,123", "1 234,5")
      v = dig(record, src.slice(10));
      if (typeof v === "string") { const t = v.trim().replace(/[\u00a0 ]/g, ""); v = /^[+-]?[0-9.]*,?[0-9]+$/.test(t) ? toNumber(t.replace(/\./g, "").replace(",", ".")) : null; }
    } else if (src.startsWith("iso:")) { // iso:<path> — epoch seconds (or milliseconds, >= 1e11) as ISO-8601 UTC; other values unchanged
      for (const alt of src.slice(4).split("|")) { v = dig(record, alt); if (v !== undefined && v !== null && v !== "") break; }
      v = epochIso(v);
    } else {
      const asStr = src.startsWith("str:"); // str:<path> — a number the vocabulary types as a string
      const asNum = src.startsWith("num:"); // num:<path> — a decimal string the vocabulary types as a number
      for (const alt of (asStr || asNum ? src.slice(4) : src).split("|")) { // a|b — the first alternative that is present
        v = dig(record, alt);
        if (v !== undefined && v !== null && v !== "") break;
      }
      if (asStr && v !== undefined && v !== null && typeof v !== "object") v = String(v);
      if (asNum && typeof v === "string") { const n = v.trim() === "" ? NaN : Number(v); v = Number.isFinite(n) ? n : null; }
    }
    out[k] = (k === "id" || k.endsWith("_id")) && v !== undefined && v !== null ? String(v) : v ?? null;
  }
  out.raw = record && typeof record === "object" && !Array.isArray(record) ? record : { values: record }; // as Python: a positional array or a scalar row lives under raw.values
  return out;
}

const PAGING = /(?:^|[^A-Za-z0-9_@])(page|page0|offset|cursor)(?:[^A-Za-z0-9_]|$)/;
/** True when the tool sends a page, offset or cursor expression anywhere (params, body, path, path_params);
 *  a tool that sends none returns the same records for every `page`, so it must not advertise a next_page. */
const NUMBERED = /(?:^|[^A-Za-z0-9_@])(page|page0|offset)(?:[^A-Za-z0-9_]|$)/;
export function paginates(tool: ToolSpec, numbered = false): boolean {
  const exprs: string[] = [];
  for (const key of ["params", "body", "path_params"] as const) {
    for (const [k, v] of Object.entries((tool as any)[key] ?? {})) {
      if (typeof v === "string") exprs.push(v);
      if (k.includes("{")) exprs.push(k);
    }
  }
  for (const m of (tool.path ?? "").matchAll(/\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g)) exprs.push(m[1]);
  // numbered: only page/page0/offset count (a cursor-only tool ignores `page`, so it never offers next_page)
  return Boolean((tool.result as any)?.slice) || exprs.some((e) => (numbered ? NUMBERED : PAGING).test(e));
}

/** Parallel arrays ({t: [1, 2], o: ["5", "6"]}, TradingView/UDF style) -> one record per index. */
function columnsToRows(cols: Record<string, unknown>): Record<string, unknown>[] {
  const arrays = Object.entries(cols).filter(([, v]) => Array.isArray(v)) as [string, unknown[]][];
  const n = arrays.reduce((m, [, v]) => Math.max(m, v.length), 0);
  return Array.from({ length: n }, (_, i) => Object.fromEntries(arrays.map(([k, v]) => [k, i < v.length ? v[i] : null])));
}

const PATH_SAFE = "!$&'()*+,;=:@/";
/** A value spliced into a URL path (adapter.py encode_path_value): characters outside RFC 3986 pchar and "/" are
 *  percent-encoded, an existing %XX escape is kept, a "." or ".." segment (also as %2E, which URL parsers resolve) is refused. */
export function encodePathValue(value: unknown): string {
  const text = String(value);
  for (const seg of text.split("/")) {
    let dec = seg; try { dec = decodeURIComponent(seg); } catch { /* a stray % is encoded below */ }
    if (dec === "." || dec === "..") throw new InvalidInput("a path argument cannot contain '.' or '..' segments");
  }
  const enc = (part: string) => [...PATH_SAFE].reduce((acc, ch) => acc.split(encodeURIComponent(ch)).join(ch), encodeURIComponent(part));
  return text.split(/(%[0-9A-Fa-f]{2})/).map((part) => (/^%[0-9A-Fa-f]{2}$/.test(part) ? part : enc(part))).join("");
}

const CURSOR_PREFIX = "pmc1.";
/** A window inside a fixed-size upstream page: pmc1.<base64url of [upstream cursor, offset]> (same bytes as the Python runtime). */
export function encodeCursor(upstream: string | null, offset: number): string {
  return CURSOR_PREFIX + Buffer.from(JSON.stringify([upstream, offset]), "utf8").toString("base64url");
}
/** [upstream cursor, offset]; anything that is not ours is the platform's own cursor at offset 0. */
export function decodeCursor(cursor: string): [string | null, number] {
  if (!cursor.startsWith(CURSOR_PREFIX)) return [cursor, 0];
  try {
    const v = JSON.parse(Buffer.from(cursor.slice(CURSOR_PREFIX.length), "base64url").toString("utf8"));
    if (Array.isArray(v) && v.length === 2 && Number.isInteger(v[1]) && v[1] >= 0 && (v[0] === null || typeof v[0] === "string")) return [v[0], v[1]];
  } catch { /* fall through */ }
  throw new InvalidInput("cursor is not one this tool returned; pass next_cursor back unchanged");
}
/** RFC 8288 Link header -> {rel: url} (same as adapter.py parse_link_header). */
export function parseLinkHeader(value: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const m of (value ?? "").matchAll(/<([^>]*)>\s*((?:;\s*[^;,]+)*)/g)) {
    const rel = /;\s*rel\s*=\s*"?([^";,]+)"?/i.exec(m[2]);
    for (const r of rel ? rel[1].split(/\s+/).filter(Boolean) : []) if (!(r.toLowerCase() in out)) out[r.toLowerCase()] = m[1];
  }
  return out;
}
/** `header:<Name>` — a response header; `link:<param>` — that query parameter of the Link rel="next" URL (`link:` alone: the URL). */
export function fromHeaders(spec: string, headers: Record<string, string>): string | null {
  if (spec.startsWith("header:")) { const v = headers[spec.slice(7).toLowerCase()]; return v === undefined || v === null || v === "" ? null : v; }
  const nxt = parseLinkHeader(headers.link ?? "").next;
  if (!nxt) return null;
  if (spec === "link:") return nxt;
  let v: string | null = null;
  try { v = new URL(nxt, "https://x.invalid/").searchParams.get(spec.slice(5)); } catch { v = null; }
  return v === null || v === "" ? null : v;
}

export const DEFAULT_CACHE_TTL = 60;
/** Seconds a successful response of this tool may be reused (see adapter.py cache_ttl_for). */
export function cacheTtlFor(tool: ToolSpec): number | undefined {
  if ("cache_ttl" in (tool as any)) return Number((tool as any).cache_ttl || 0) || undefined;
  const r: any = tool.result ?? {};
  if (r.slice || r.trim) { const env = process.env.PLATFORM_MCP_CACHE_TTL; const n = env === undefined ? DEFAULT_CACHE_TTL : Number(env); return Number.isFinite(n) ? n || undefined : DEFAULT_CACHE_TTL; }
  return undefined;
}
/** result.filter [{arg, fields, match: contains|equals, value?}] (see adapter.py apply_filters). */
function applyFilters(items: Record<string, unknown>[], rules: any[] | undefined, args: Record<string, unknown>, evalExpr: (e: unknown) => unknown): Record<string, unknown>[] {
  for (const rule of rules ?? []) {
    const want = rule.value ? evalExpr(rule.value) : args[rule.arg];
    if (want === undefined || want === null || want === "") continue;
    const wants = (Array.isArray(want) ? want : [want]).map((w) => String(w).toLowerCase());
    const mode = rule.match || "contains";
    const ok = (text: string, w: string) => (mode === "equals" ? text === w : mode === "gte" ? text >= w : mode === "lte" ? text.slice(0, w.length) <= w : text.includes(w)); // gte/lte: ISO dates as strings
    items = items.filter((item) => (rule.fields ?? [rule.arg]).some((f: string) => {
      const v = dig(item, f);
      if (v === undefined || v === null || typeof v === "object") return false;
      const text = String(v).toLowerCase();
      return wants.some((w) => ok(text, w));
    }));
  }
  return items;
}

export class Adapter {
  constructor(private spec: Spec, private transport: Transport, private creds: Record<string, string> = {}) {}
  supports(verb: string): boolean { return verb in this.spec.adapter.tools; }
  async call(verb: string, args: Record<string, unknown>): Promise<Record<string, unknown>> {
    const tool = this.spec.adapter.tools[verb];
    if (!tool) throw new NotSupported(`${this.spec.id} does not offer ${verb}`);
    const result = tool.result ?? {};
    let read: boolean; // read or write by the vocabulary (GraphQL and SOAP reads are POSTs); the method when the verb is unknown
    try { read = Boolean(vocabFor(this.spec as any)[verb].read_only); } catch { read = (tool.method ?? "GET").toUpperCase() === "GET"; }
    if (this.spec.category === "generic") { // tools defined by the API's own operations: the answer is passed through (generic.ts)
      const data = await this.request(tool, args, cacheTtlFor(tool), false, read);
      return genericShape(data, tool as any, args);
    }
    let skip = 0; let usedCursor: string | null = null;
    if ((result as any).trim && args.cursor) { // our own cursor (pmc1.<base64url [upstream cursor, offset]>) addresses a window inside a fixed-size upstream page
      [usedCursor, skip] = decodeCursor(String(args.cursor));
      args = { ...args, cursor: usedCursor };
    }
    let data: any; let headers: Record<string, string> = {};
    const fromHdr = (k: string) => typeof (result as any)[k] === "string" && /^(link|header):/.test((result as any)[k]);
    if (fromHdr("next_cursor") || fromHdr("total")) { // paging carried in response headers (GitLab keyset Link, X-Total)
      const got: any = await this.request(tool, args, cacheTtlFor(tool), true, read); data = got.data; headers = got.headers ?? {};
    } else data = await this.request(tool, args, cacheTtlFor(tool), false, read);
    if (data && typeof data === "object" && (data as any).__unparsed__ !== undefined && (result.items !== undefined || result.fields)) {
      const snippet = String((data as any).text).split(/\s+/).filter(Boolean).join(" ").slice(0, 200);
      // the entry's error_kinds (status 200) first (BCB: a 200 HTML 'Requisição inválida!' page), then a throttle notice is rate_limited
      const text = String((data as any).text);
      const rule = ((this.transport as any).errorKinds ?? []).find((r: any) => r && typeof r === "object" && String(r.kind) in KINDS
        && (r.status === undefined || r.status === null || (Array.isArray(r.status) ? r.status : [r.status]).includes(200))
        && (!r.match || text.toLowerCase().includes(String(r.match).toLowerCase())));
      const Kind = rule ? KINDS[String(rule.kind)] : RATE_WORDS.test(text.slice(0, 2000).toLowerCase()) ? RateLimited : PlatformError;
      throw new Kind(scrub(`the platform answered ${String((data as any).__unparsed__).split(";")[0] || "a body"} that is not JSON, XML or CSV: ${snippet}`));
    }
    if (tool.kind === "probe") return { ok: true, account: data && typeof data === "object" && !Array.isArray(data) ? data : {} };
    // {arg} in a result path: CTFtime results are keyed by event id -> items "{competition_id}.scores"
    const argPath = (path?: string) => (typeof path === "string" && path.includes("{") ? path.replace(/\{([A-Za-z_][A-Za-z0-9_]*)\}/g, (_m, n) => (args[n] === undefined || args[n] === null || args[n] === "" ? "\u0000" : String(args[n]))) : path);
    if (result.items !== undefined) {
      let rows: any = dig(data, argPath(result.items)) ?? [];
      if ((result as any).columnar && rows && typeof rows === "object" && !Array.isArray(rows)) rows = columnsToRows(rows as Record<string, unknown>);
      else if (rows && typeof rows === "object" && !Array.isArray(rows)) rows = (result as any).items_are_values ? Object.entries(rows).map(([k, v]) => (v && typeof v === "object" && !Array.isArray(v) ? { ...(v as object), _key: k } : v)) : [rows]; // collections keyed by id
      // result.scalar_rows: a list of plain values (Gemini /v1/symbols) — each value is a record named `$` in result.fields
      rows = (rows as unknown[]).filter((r) => (r && typeof r === "object") || ((result as any).scalar_rows && r !== null && r !== undefined && typeof r !== "boolean"));
      const page = Number(args.page ?? 1); let limit = Number(args.limit ?? tool.default_limit ?? 25);
      const fields = result.fields ?? {}; const listKey = result.key ?? "items";
      if ((result as any).slice) { // the platform answers the whole collection: apply page/limit here (capped by max_limit)
        limit = Math.min(limit, Number(tool.max_limit ?? 100));
        const lo = (page - 1) * limit; const hi = page * limit;
        if (!(result.require?.length || (result as any).sort || (result as any).filter)) { // nothing depends on other rows' mapped values: map only this page
          return { [listKey]: rows.slice(lo, hi).map((r: unknown) => mapFields(r, fields, args)), total: rows.length, next_page: hi < rows.length ? page + 1 : null };
        }
        let items = rows.map((r: unknown) => mapFields(r, fields, args));
        if (result.require?.length) items = items.filter((i: Record<string, unknown>) => result.require!.every((k) => i[k] !== null && i[k] !== undefined));
        items = applyFilters(items, (result as any).filter, args, (e) => this.value(e, args, tool));
        const every = items.length;
        const key = (result as any).sort as string | undefined; // no stable order upstream: sort on a normalised field so pages do not overlap
        if (key) items.sort((a: any, b: any) => { const x = a[key] == null ? "" : String(a[key]); const y = b[key] == null ? "" : String(b[key]); return x < y ? -1 : x > y ? 1 : 0; });
        return { [listKey]: items.slice(lo, hi), total: every, next_page: hi < every ? page + 1 : null };
      }
      let items = rows.map((r: unknown) => mapFields(r, fields, args));
      if (result.require?.length) items = items.filter((i: Record<string, unknown>) => result.require!.every((k) => i[k] !== null && i[k] !== undefined)); // feed headers, legal notices
      items = applyFilters(items, (result as any).filter, args, (e) => this.value(e, args, tool)); // filters on a verb that does not page (SNB long-format CSV)
      limit = effectiveLimit(tool, args); // the page size actually requested (capped by max_limit)
      items = applyCap(items, result, limit);
      const totalRaw = result.total ? (fromHdr("total") ? fromHeaders(result.total, headers) : dig(data, result.total)) : undefined;
      const total = typeof totalRaw === "number" ? Math.trunc(totalRaw) : typeof totalRaw === "string" && /^\d+$/.test(totalRaw.trim()) ? Number(totalRaw.trim()) : null;
      const out: Record<string, unknown> = { [listKey]: items, total, next_page: paginates(tool, true) && items.length >= limit && (total === null || page * limit < total) ? page + 1 : null };
      if ((result as any).next_cursor) { // cursor-paginated APIs: pass next_cursor back as `cursor`
        const nxt = fromHdr("next_cursor") ? fromHeaders((result as any).next_cursor, headers) : dig(data, (result as any).next_cursor);
        out.next_cursor = nxt === undefined || nxt === null || nxt === "" || nxt === false ? null : String(nxt);
        if (out.next_cursor !== null && args.cursor !== undefined && args.cursor !== null && args.cursor !== "" && out.next_cursor === String(args.cursor)) out.next_cursor = null; // the platform handed back the cursor it was given: following it would loop forever
        if ((result as any).trim) { // the platform ignores the page size: return `limit` rows and a cursor to the rest of this upstream page first
          limit = Math.min(limit, Number(tool.max_limit ?? 100));
          out[listKey] = items.slice(skip, skip + limit);
          if (skip + limit < items.length) out.next_cursor = encodeCursor(usedCursor, skip + limit);
        }
        if (out.next_cursor === null) out.next_page = null;
      }
      return out;
    }
    if (result.fields) {
      const record = dig(data, argPath(result.root));
      if (!record || typeof record !== "object" || Array.isArray(record) || Object.keys(record as object).length === 0) {
        const vals = Object.values(result.fields);
        if (vals.length && vals.every((v) => typeof v === "string" && v.startsWith("="))) return mapFields({}, result.fields, args); // a write that answers 204/empty: the literals are the result
        if (read) throw new NotFound("platform returned no record", { status: 404 }); // a read verb (GraphQL/SOAP reads are POSTs)
        throw new InvalidInput("platform returned no record", { status: 404 });
      }
      return mapFields(record as Record<string, unknown>, result.fields, args);
    }
    return { raw: data };
  }
  private value(expr: unknown, args: Record<string, unknown>, tool: ToolSpec): unknown {
    if (typeof expr === "string" && expr.startsWith("=")) return expr.slice(1);
    if (typeof expr === "string" && expr.startsWith("json:")) return JSON.parse(expr.slice(5)); // typed literal
    if (typeof expr === "string" && expr.startsWith("str:")) {
      const inner = this.value(expr.slice(4), args, tool);
      if (inner == null) return undefined;
      if (typeof inner === "number" && /e/i.test(String(inner))) return inner.toFixed(20).replace(/0+$/, "").replace(/\.$/, ""); // never scientific notation
      return String(inner);
    }
    if (typeof expr === "string" && expr.startsWith("jsonstr:")) {
      // jsonstr:{"text":{text}} — a JSON document serialized to a string; each {expr} becomes a JSON value
      let missing = false;
      const text = expr.slice(8).replace(/\{([A-Za-z_@][A-Za-z0-9_.:@]*)\}/g, (_m, e) => { const v = this.value(e, args, tool); if (v === undefined || v === null) missing = true; return JSON.stringify(v ?? null); });
      return missing ? undefined : JSON.stringify(JSON.parse(text));
    }
    if (typeof expr === "string" && expr.startsWith("fmt:")) {
      // fmt:customers/{@customer_id}/campaigns/{campaign_id} — each {expr} is any expression
      let missing = false;
      const render = (tpl: string): [string, boolean] => { let miss = false; const t = tpl.replace(/\{([^{}]+)\}/g, (_m, e) => { const v = this.value(e, args, tool); if (v === undefined || v === null || v === "") { miss = true; return ""; } return String(v); }); return [t, miss]; };
      // [?optional part]: a group written [?...] holding an {expr} is left out when any of its expressions is missing
      // one pass, so a value containing braces is never expanded again
      const out = expr.slice(4).replace(/\[\?([^\[\]{}]*(?:\{[^{}]+\}[^\[\]{}]*)+)\]|\{([^{}]+)\}/g, (m0, inner, single) => {
        if (single !== undefined) { const [t, miss] = render(m0); if (miss) missing = true; return t; }
        const [t, miss] = render(inner); return miss ? "" : t;
      });
      return missing ? undefined : out;
    }
    if (typeof expr === "string" && expr.startsWith("date:")) {
      // date:<expr> — the value only if it is exactly an ISO date (safe to splice into a query language)
      const v = this.value(expr.slice(5), args, tool);
      if (v === undefined || v === null || v === "") return undefined;
      if (!/^\d{4}-\d{2}-\d{2}$/.test(String(v))) throw new InvalidInput(`${expr.slice(5)} must be an ISO date (YYYY-MM-DD), got ${JSON.stringify(v)}`);
      return String(v);
    }
    if (typeof expr === "string" && /^(year|month|day):/.test(expr)) {
      // year:/month:/day:<expr> — integer part of an ISO date (Rest.li dateRange)
      const part = expr.slice(0, expr.indexOf(":")); const inner = expr.slice(expr.indexOf(":") + 1);
      const v = this.value(inner, args, tool);
      if (v === undefined || v === null || v === "") return undefined;
      const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(v));
      if (!m) throw new InvalidInput(`${inner} must be an ISO date (YYYY-MM-DD), got ${JSON.stringify(v)}`);
      return Number(m[{ year: 1, month: 2, day: 3 }[part as "year" | "month" | "day"]]);
    }
    if (typeof expr === "string" && expr.startsWith("map:")) {
      // map:<expr>:pause=PAUSED,resume=ENABLED — translate a vocabulary enum to the platform's value
      const rest = expr.slice(4); const eq = rest.indexOf("="); const cut = rest.lastIndexOf(":", eq < 0 ? rest.length : eq); // table starts after the last ':' before the first '='

      const inner = rest.slice(0, cut);
      const pairs = Object.fromEntries(rest.slice(cut + 1).split(",").filter((x) => x.includes("=")).map((x) => [x.slice(0, x.indexOf("=")), x.slice(x.indexOf("=") + 1)]));
      const v = this.value(inner, args, tool);
      if (v === undefined || v === null) return undefined;
      if (!(String(v) in pairs)) throw new InvalidInput(`${inner} must be one of ${JSON.stringify(Object.keys(pairs).sort())}, got ${JSON.stringify(v)}`);
      const out = pairs[String(v)];
      return out.startsWith("json:") ? JSON.parse(out.slice(5)) : out; // typed target: map:action:pause=json:false
    }
    if (typeof expr === "string" && expr.startsWith("int:")) {
      const inner = this.value(expr.slice(4), args, tool);
      if (inner == null || inner === "") return undefined;
      const n = Number(inner);
      if (!Number.isInteger(n)) throw new InvalidInput(`${expr.slice(4)} must be an integer, got ${JSON.stringify(inner)}`);
      return n;
    }
    if (typeof expr === "string" && /^(epoch|epoch_ms):/.test(expr)) {
      const kind = expr.slice(0, expr.indexOf(":")); const v = this.value(expr.slice(expr.indexOf(":") + 1), args, tool);
      if (v === undefined || v === null || v === "") return undefined;
      const ms = parseWhen(v).getTime(); return kind === "epoch_ms" ? ms : Math.floor(ms / 1000);
    }
    if (expr === "now_epoch") return Math.floor(Date.now() / 1000);
    if (expr === "now_epoch_ms") return Date.now();
    if (expr === "today") return new Date().toISOString().slice(0, 10);
    if (typeof expr === "string" && /^(days_ago|days_ahead):/.test(expr)) {
      const [kind, n] = expr.split(":"); const d = new Date(Date.now() + (kind === "days_ahead" ? 1 : -1) * Number(n) * 86400000);
      return d.toISOString().slice(0, 10);
    }
    if (typeof expr === "string" && expr.startsWith("datefmt:")) {
      const rest = expr.slice(8); const cut = rest.includes("%") ? rest.indexOf(":", rest.lastIndexOf("%") + 2) : rest.indexOf(":");
      const v = this.value(rest.slice(cut + 1), args, tool);
      if (v === undefined || v === null || v === "") return undefined;
      return fmtWhen(rest.slice(0, cut), parseWhen(v));
    }
    if (typeof expr === "string" && /^(minor|micros|mul):/.test(expr)) {
      let factor: string, inner: string;
      if (expr.startsWith("mul:")) { const parts = expr.split(":"); factor = parts[1]; inner = parts.slice(2).join(":"); }
      else { factor = expr.startsWith("minor:") ? "100" : "1000000"; inner = expr.slice(expr.indexOf(":") + 1); }
      const v = this.value(inner, args, tool);
      if (v === undefined || v === null || v === "") return undefined;
      try { return scaleInt(v, factor); } catch { throw new InvalidInput(`${inner} must be a number, got ${JSON.stringify(v)}`); }
    }
    if (typeof expr === "string" && expr.startsWith("part:")) { // part:<n>:<expr> — the n-th '/'-separated part of a value (a two-dimensional series id)
      const rest = expr.slice(5); const n = Number(rest.slice(0, rest.indexOf(":"))); const v = this.value(rest.slice(rest.indexOf(":") + 1), args, tool);
      if (v === undefined || v === null || v === "") return undefined;
      const parts = String(v).split("/");
      return n < parts.length && parts[n] !== "" ? parts[n] : undefined;
    }
    if (expr === "cursor") return (args.cursor as string) || undefined;
    if (typeof expr === "string" && expr.startsWith("jsonpart:")) { const v = this.value(expr.slice(9), args, tool); return v === undefined || v === null ? undefined : { _json_part: v }; } // multipart part sent as application/json
    if (typeof expr === "string" && expr.startsWith("file:")) { // a file part for multipart bodies, downloaded from a URL argument
      const v = this.value(expr.slice(5), args, tool);
      return v === undefined || v === null || v === "" ? undefined : { _file_url: String(v) };
    }
    const page = Number(args.page ?? 1);
    if (expr === "offset") return (page - 1) * effectiveLimit(tool, args); // the page size actually sent: an uncapped limit would skip rows
    if (expr === "limit") return effectiveLimit(tool, args);
    if (expr === "page") return page;
    if (expr === "page0") return page - 1;
    if (expr === "uuid") return crypto.randomUUID(); // client-generated transaction / idempotency ids
    if (expr === "now") return new Date().toISOString();
    if (typeof expr === "string" && expr.startsWith("@")) return this.creds[expr.slice(1)];
    if (typeof expr === "string" && expr.includes(".")) return dig(args, expr); // an element of an array argument: image_urls.0
    return typeof expr === "string" ? args[expr] : undefined;
  }
  private async request(tool: ToolSpec, args: Record<string, unknown>, cacheTtl?: number, wantHeaders = false, read?: boolean): Promise<unknown> {
    const params: Record<string, unknown> = {};
    for (const [k, expr] of Object.entries(tool.params ?? {})) params[k] = this.value(expr, args, tool);
    Object.assign(params, tool.fixed_params ?? {});
    let path = tool.path;
    const auth = this.spec.adapter.auth ?? {};
    for (const m of path.matchAll(/\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g)) {
      if ((auth.type === "path" && m[1] === (auth.field ?? "token")) || (m[1] === "access_token" && !(m[1] in args))) continue; // the transport fills the credential / minted-token placeholder
      let v = args[m[1]];
      if ((v === undefined || v === null || v === "") && tool.path_params && m[1] in tool.path_params) v = this.value(tool.path_params[m[1]], args, tool);
      if (v === undefined || v === null || v === "") throw new InvalidInput(`missing argument '${m[1]}'` + (tool.path_params && m[1] in tool.path_params ? ` (built from '${String(tool.path_params[m[1]])}': give the arguments it reads)` : ""));
      const enc = encodePathValue(v); // no query, fragment or dot segments from an argument
      path = path.replace(m[0], () => enc);
    }
    let body: any;
    if (tool.body) {
      body = Object.keys(tool.body).every((k) => /^\d+$/.test(splitKey(k)[0])) ? [] : {}; // index-led keys build a top-level array
      for (const [k, expr] of Object.entries(tool.body)) {
        const v = this.value(expr, args, tool);
        if (v === undefined || v === null) continue;
        const key = k.includes("{") ? k.replace(/\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g, (_m, e) => String(this.value(e, args, tool))) : k; // "updates.{item_id}.quantity"
        setPath(body, splitKey(key), v); // dotted keys build objects, digit segments build arrays
      }
    }
    return this.transport.request(tool.method ?? "GET", path, params, body, (tool as any).body_format === "form", (tool as any).headers ?? {}, (tool as any).query_safe ?? "", (tool as any).sign !== false, (tool as any).body_format === "xml" ? (tool as any).xml_root : undefined, (tool as any).body_format === "multipart", cacheTtl, wantHeaders, (tool as any).csv, read);
  }
}
