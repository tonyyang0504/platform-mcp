import crypto from "node:crypto";
import fs from "node:fs";
import { XMLParser } from "fast-xml-parser";
import { registerSecret, scrub } from "./credentials.js";
import { AuthError, InvalidInput, PlatformError, RateLimited, classify, messageFor, type ErrorRule } from "./errors.js";
import { checkUrl, defaultResolver, pick, pinnedGet, type Resolver } from "./netguard.js";
import { dig } from "./adapter.js";

export interface AuthSpec {
  type?: "none" | "bearer" | "header" | "basic" | "query" | "path" | "session" | "oauth2_client_credentials" | "oauth2_refresh_token";
  login?: { method?: string; path: string; body?: Record<string, string> };
  token_url?: string; client_id_field?: string; client_secret_field?: string; grant?: string; scope?: string;
  refresh_token_field?: string; client_auth?: "basic" | "body"; token_params?: Record<string, string>; extra_headers?: Record<string, string>;
  token_path?: string; expires_path?: string; token_ttl_seconds?: number;
  field?: string; header?: string; prefix?: string; param?: string;
  /** several credential-carrying headers (header name -> credential field) / query parameters (parameter name -> credential field) */
  headers?: Record<string, string>; params?: Record<string, string>;
  username_field?: string; password_field?: string; password?: string;
  fields?: { name: string; required?: boolean; help?: string }[];
}

class TokenBucket {
  private tokens: number; private updated = Date.now(); private queue: Promise<void> = Promise.resolve();
  constructor(private rate: number, private capacity = Math.max(Math.floor(rate), 1)) { this.tokens = this.capacity; }
  /** One caller at a time (the Python runtime holds a lock): concurrent calls would otherwise all sleep the same
   *  interval and fire together, far above rate_per_second. */
  take(): Promise<void> {
    const turn = this.queue.then(() => this.takeOne());
    this.queue = turn.catch(() => undefined);
    return turn;
  }
  private async takeOne(): Promise<void> {
    const now = Date.now();
    this.tokens = Math.min(this.capacity, this.tokens + ((now - this.updated) / 1000) * this.rate);
    this.updated = now;
    if (this.tokens < 1) {
      await new Promise((r) => setTimeout(r, ((1 - this.tokens) / this.rate) * 1000));
      this.tokens = 0;
      this.updated = Date.now(); // the token earned while sleeping was just spent: refill from now
    } else this.tokens -= 1;
  }
}

const XML = new XMLParser({ ignoreAttributes: false, attributeNamePrefix: "@", textNodeName: "#text", parseTagValue: false, parseAttributeValue: false, trimValues: true, ignoreDeclaration: true, removeNSPrefix: true, htmlEntities: true }); // htmlEntities: numeric character references (&#038; &#8217;) decode as in the Python runtime
/** XML → {root: …} in the same shape as the Python runtime's xml_to_obj. */
export function xmlToObj(text: string): Record<string, unknown> { return trimText(XML.parse(text)) as Record<string, unknown>; }
/** Element text is trimmed like the Python runtime's `el.text.strip()` — including CDATA sections, which
 *  fast-xml-parser leaves untouched (a feed title `<![CDATA[Designer ]]>` must read "Designer" in both). */
function trimText(v: unknown, key = ""): unknown {
  if (typeof v === "string") return key.startsWith("@") ? v : v.trim();
  if (Array.isArray(v)) return v.map((x) => trimText(x, key));
  if (v && typeof v === "object") return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, trimText(x, k)]));
  return v;
}
const esc = (x: string) => x.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
/** Request bodies: dict keys → elements, arrays → repeated elements, `@x` → attributes (Python obj_to_xml). */
export function objToXml(root: string, obj: unknown): string {
  const node = (name: string, val: any): string => {
    if (Array.isArray(val)) return val.map((v) => node(name, v)).join("");
    if (val && typeof val === "object") {
      const attrs = Object.entries(val).filter(([k]) => k.startsWith("@")).map(([k, v]) => ` ${k.slice(1)}="${esc(String(v)).replace(/"/g, "&quot;")}"`).join("");
      let inner = Object.entries(val).filter(([k]) => !k.startsWith("@") && k !== "#text").map(([k, v]) => node(k, v)).join("");
      if ("#text" in val) inner += esc(String(val["#text"]));
      return `<${name}${attrs}>${inner}</${name}>`;
    }
    if (typeof val === "boolean") val = val ? "true" : "false";
    return `<${name}>${esc(val === null || val === undefined ? "" : String(val))}</${name}>`;
  };
  return '<?xml version="1.0" encoding="UTF-8"?>' + node(root, obj);
}
function setNested(root: Record<string, any>, key: string, value: unknown): void {
  const parts = key.split("."); let cur = root;
  for (const part of parts.slice(0, -1)) cur = cur[part] ??= {};
  cur[parts[parts.length - 1]] = value;
}

/** [present, value] for a dotted path (`*` and array indexes as in adapter.dig): an absent key is not a null. */
function digFound(data: unknown, path: string): [boolean, unknown] {
  let cur: any = data;
  for (const part of path.split(".")) {
    if (part === "*" && cur && typeof cur === "object" && !Array.isArray(cur) && Object.keys(cur).length) cur = Object.values(cur)[0];
    else if (part === "*" && Array.isArray(cur) && cur.length) cur = cur[0];
    else if (cur && typeof cur === "object" && !Array.isArray(cur) && Object.prototype.hasOwnProperty.call(cur, part)) cur = cur[part];
    else if (Array.isArray(cur) && /^\d+$/.test(part) && Number(part) < cur.length) cur = cur[Number(part)];
    else return [false, undefined];
  }
  return [true, cur];
}
/** A message from any JSON value, identical in both runtimes (strings as-is, the rest as compact JSON). */
const jsonText = (v: unknown): string => (typeof v === "string" ? v : JSON.stringify(v) ?? "null");

/** The body as text, decoded as in the Python runtime: the Content-Type charset, else the encoding an XML declaration
 *  names (windows-1251 at the Bank of Russia), else UTF-8. fetch's text() always decodes UTF-8, so the bytes are read. */
export async function bodyText(resp: any): Promise<string> {
  if (typeof resp.arrayBuffer !== "function") return resp.text(); // a mocked fetcher
  const buf = Buffer.from(await resp.arrayBuffer());
  const ctype = resp.headers.get("content-type") ?? "";
  let enc = /charset\s*=\s*["']?([A-Za-z0-9_.:-]+)/i.exec(ctype)?.[1];
  if (!enc) enc = /^\s*<\?xml[^>]*?encoding\s*=\s*["']([A-Za-z0-9_.:-]+)["']/.exec(buf.subarray(0, 300).toString("latin1").replace(/^\ufeff/, ""))?.[1] ?? "utf-8";
  let decoder: TextDecoder;
  try { decoder = new TextDecoder(enc); } catch { decoder = new TextDecoder("utf-8"); } // an unknown label (BCB declares encoding="pt-br")
  return decoder.decode(buf); // TextDecoder drops a UTF-8 BOM and replaces undecodable bytes with U+FFFD, as Python's decode(errors="replace")
}

/** A body that is not JSON, XML or CSV ({text}): marked (non-enumerable) so a tool that maps records from it fails instead of answering an empty success. */
export function unparsed(text: string, ctype: string): Record<string, unknown> {
  const out: Record<string, unknown> = { text };
  Object.defineProperty(out, "__unparsed__", { value: ctype || "", enumerable: false });
  return out;
}
/** Response headers as a lower-case map (the mocked fetchers in tests may only implement get()). */
function headerMap(h: any): Record<string, string> {
  const out: Record<string, string> = {};
  if (h && typeof h.forEach === "function") h.forEach((v: string, k: string) => { out[k.toLowerCase()] = v; });
  else for (const k of ["link", "x-total", "x-total-count", "x-next-page", "x-total-pages", "content-type"]) { const v = h?.get?.(k); if (v !== null && v !== undefined) out[k] = v; }
  return out;
}

/** RFC 4180 CSV → array of row objects keyed by the header row (same result as Python's csv.DictReader). */
function parseCsv(text: string, delimiter = ","): Record<string, string>[] {
  const rows: string[][] = []; let row: string[] = []; let cell = ""; let q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) { if (c === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; } else cell += c; }
    else if (c === '"') q = true;
    else if (c === delimiter) { row.push(cell); cell = ""; }
    else if (c === "\n" || c === "\r") { if (c === "\r" && text[i + 1] === "\n") i++; row.push(cell); cell = ""; rows.push(row); row = []; }
    else cell += c;
  }
  if (cell !== "" || row.length) { row.push(cell); rows.push(row); }
  const [head, ...body] = rows.filter((r) => !(r.length === 1 && r[0] === ""));
  // as Python's DictReader: a missing cell is null; blank header columns and all-empty rows are dropped
  return (body ?? []).map((r) => Object.fromEntries((head ?? []).map((h, i) => [h, r[i] ?? null] as [string, string | null]).filter(([h]) => h !== "")))
    .filter((o) => Object.values(o).some((v) => v !== null && v !== "")) as Record<string, string>[];
}

/** application/x-www-form-urlencoded: scalars as-is, arrays as repeated keys, objects as JSON. */
function formBody(body: Record<string, unknown>): string {
  const f = new URLSearchParams();
  for (const [k, v] of Object.entries(body)) {
    if (Array.isArray(v)) for (const x of v) f.append(k, String(x));
    else if (v && typeof v === "object") f.append(k, JSON.stringify(v));
    else f.append(k, String(v));
  }
  return f.toString();
}

export function authHeaders(auth: AuthSpec, creds: Record<string, string>): Record<string, string> {
  const extra = Object.fromEntries(Object.entries(auth.extra_headers ?? {}).filter(([, f]) => creds[f]).map(([h, f]) => [h, creds[f]]));
  switch (auth.type ?? "none") {
    case "none": case "query": case "path": case "session": case "oauth2_client_credentials": case "oauth2_refresh_token": return extra;
    case "bearer": return { ...extra, Authorization: `Bearer ${creds[auth.field ?? "token"]}` };
    case "header": {
      if (auth.headers) return { ...extra, ...Object.fromEntries(Object.entries(auth.headers).filter(([, f]) => creds[f]).map(([h, f]) => [h, creds[f]])) };
      return { ...extra, [auth.header!]: (auth.prefix ?? "") + creds[auth.field ?? "api_key"] };
    }
    case "basic": {
      const user = auth.username_field ? creds[auth.username_field] ?? "" : creds[auth.field ?? "api_key"];
      const pwd = auth.password_field ? creds[auth.password_field] ?? "" : auth.password ?? "";
      const token = Buffer.from(`${user}:${pwd}`).toString("base64");
      registerSecret(token); // an error body that echoes the Authorization header is redacted too
      return { ...extra, Authorization: "Basic " + token };
    }
  }
  throw new InvalidInput(`unsupported auth type ${auth.type} in catalog`);
}

/** Credential-carrying query parameters: `type: query` with one `param`/`field` pair, and/or a `params` map usable with any auth type. Optional credentials that were not supplied are left out. */
export function authParams(auth: AuthSpec, creds: Record<string, string>): Record<string, string> {
  const out: Record<string, string> = {};
  if (auth.type === "query" && auth.param) { const v = creds[auth.field ?? "api_key"]; if (v) out[auth.param] = v; }
  for (const [param, field] of Object.entries(auth.params ?? {})) { const v = creds[field]; if (v) out[param] = v; }
  return out;
}

export type Fetcher = (url: string, init: { method: string; headers: Record<string, string>; body?: any; redirect?: "manual" }) => Promise<{ status: number; headers: { get(k: string): string | null }; text(): Promise<string> }>;

/** Stable JSON (sorted object keys) for cache keys. */
function stableJson(v: unknown): string {
  if (Array.isArray(v)) return "[" + v.map(stableJson).join(",") + "]";
  if (v && typeof v === "object") return "{" + Object.keys(v as object).sort().map((k) => JSON.stringify(k) + ":" + stableJson((v as any)[k])).join(",") + "}";
  return JSON.stringify(v ?? null);
}

/** A short-lived, bounded cache of successful response bodies (text, so memory is bounded by the bytes held):
 *  LRU, per-entry TTL, total capped by PLATFORM_MCP_CACHE_MAX_MB (default 64) and PLATFORM_MCP_CACHE_MAX_ENTRIES (default 16);
 *  a body larger than the cap is never stored; PLATFORM_MCP_CACHE_MAX_MB=0 disables it. Same policy as the Python runtime. */
export class ResponseCache {
  maxBytes: number; maxEntries: number; enabled: boolean; bytes = 0; hits = 0; misses = 0;
  private entries = new Map<string, [number, number, string, string, Record<string, string>]>();
  constructor(maxBytes?: number, maxEntries?: number) {
    const num = (name: string, d: number) => { const x = Number(process.env[name] ?? d); return Number.isFinite(x) ? x : d; };
    this.maxBytes = Math.trunc(maxBytes ?? num("PLATFORM_MCP_CACHE_MAX_MB", 64) * 1_000_000);
    this.maxEntries = Math.trunc(maxEntries ?? num("PLATFORM_MCP_CACHE_MAX_ENTRIES", 16));
    this.enabled = this.maxBytes > 0 && this.maxEntries > 0;
  }
  get(key: string): [string, string, Record<string, string>] | undefined {
    const item = this.entries.get(key);
    if (!item || item[0] < performance.now()) { if (item) this.drop(key); this.misses++; return undefined; }
    this.entries.delete(key); this.entries.set(key, item); this.hits++; // most recently used last
    return [item[2], item[3], item[4] ?? {}];
  }
  put(key: string, text: string, ctype: string, ttlSeconds: number, headers: Record<string, string> = {}): void {
    const size = Buffer.byteLength(text, "utf8");
    if (!this.enabled || ttlSeconds <= 0 || size > this.maxBytes) return;
    this.drop(key);
    while (this.entries.size && (this.bytes + size > this.maxBytes || this.entries.size >= this.maxEntries)) this.drop(this.entries.keys().next().value as string);
    this.entries.set(key, [performance.now() + ttlSeconds * 1000, size, text, ctype, { ...headers }]); this.bytes += size;
  }
  private drop(key: string): void { const item = this.entries.get(key); if (item) { this.entries.delete(key); this.bytes -= item[1]; } }
}

export class Transport {
  private bucket: TokenBucket;
  /** `{token}`-style credential or config placeholders in the base URL or path (a per-install `{instance}` host). */
  private fillPath(url: string): string {
    for (const [name, value] of Object.entries(this.creds)) if (value != null && url.includes(`{${name}}`)) url = url.split(`{${name}}`).join(String(value));
    if (url.includes("{access_token}") && this.token) url = url.split("{access_token}").join(this.token); // the minted session token in the URL path
    return url;
  }
  /** adapter.headers: static per-platform headers (API tier, version pins). */
  public fixedHeaders: Record<string, string> = {};
  /** adapter.error_kinds: per-entry overrides of the error table for vendors that misuse status codes. */
  public errorKinds: ErrorRule[] = [];
  constructor(private baseUrl: string, private auth: AuthSpec, public readonly creds: Record<string, string>, ratePerSecond: number, private userAgent: string, private fetcher: Fetcher = fetch as unknown as Fetcher, private envelope: { ok_field?: string; error_field?: string; ok_value?: unknown } = {}) {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
    for (const f of (auth as any).fields ?? []) registerSecret(creds[typeof f === "string" ? f : f.name]); // redact secret values everywhere
    this.loadRotatedRefreshToken();
    this.bucket = new TokenBucket(Math.max(ratePerSecond, 0.01));
  }
  private token?: string; private tokenExpires = 0;
  private async acquireToken(): Promise<string> {
    const a = this.auth; let resp;
    const nowCtx: Record<string, string> = { timestamp: String(Date.now()), timestamp_s: String(Math.floor(Date.now() / 1000)) };
    const tj = (a as any).token_jwt;
    if (tj) { // a JWT built for the token request (client_assertion / private_key_jwt, or a login body field)
      const jc: Record<string, string> = { ...nowCtx, nonce: crypto.randomUUID().replace(/-/g, "") };
      const claims: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(tj.claims ?? {})) {
        if (typeof v === "string" && /^\+\d+$/.test(v)) claims[k] = Number(jc.timestamp_s) + Number(v.slice(1));
        else { const r = this.render(String(v), jc); claims[k] = /^\d+$/.test(r) && ["{timestamp}", "{timestamp_s}"].includes(String(v)) ? Number(r) : r; }
      }
      const alg = ({ jwt_hs256: "HS256", jwt_rs256: "RS256", jwt_ps256: "PS256" } as Record<string, string>)[tj.mode ?? "jwt_rs256"];
      const hdr = Object.fromEntries(Object.entries(tj.jwt_header ?? {}).map(([k, v]) => [k, this.render(String(v), jc)]));
      const b64 = (o: unknown) => Buffer.from(JSON.stringify(o)).toString("base64url");
      const head = b64({ alg, typ: "JWT", ...hdr }) + "." + b64(claims);
      const pem = (this.creds[tj.key_field ?? "private_key"] ?? "").replace(/\\n/g, "\n");
      const sig = alg === "HS256" ? crypto.createHmac("sha256", tj.key_encoding ? this.keyBytes(tj) : pem).update(head).digest("base64url")
        : alg === "PS256" ? crypto.sign("sha256", Buffer.from(head), { key: pem, padding: crypto.constants.RSA_PKCS1_PSS_PADDING, saltLength: 32 }).toString("base64url")
        : crypto.createSign("RSA-SHA256").update(head).sign(pem, "base64url");
      nowCtx.client_assertion = `${head}.${sig}`;
    }
    if (a.type === "session") {
      const login = a.login!;
      const url = this.fillPath(login.path.startsWith("http") ? login.path : this.baseUrl + login.path);
      const body: Record<string, any> = {};
      for (const [k, v] of Object.entries(login.body ?? {})) {
        const val = typeof v === "string" && v.startsWith("@") && !v.includes("{") ? this.creds[v.slice(1)] : typeof v === "string" && v.includes("{") ? this.render(v, nowCtx) : v;
        setNested(body, k, val); // nested login bodies: auth.username
      }
      const lh: Record<string, string> = Object.fromEntries(Object.entries((login as any).headers ?? {}).map(([h, t]) => [h, this.render(String(t), nowCtx)]));
      const m = (login.method ?? "POST").toUpperCase();
      if (m === "GET") { const u = new URL(url); for (const [k, v] of Object.entries(body)) u.searchParams.set(k, String(v)); resp = await this.fetcher(u.toString(), { method: "GET", headers: { Accept: "application/json", "User-Agent": this.userAgent, ...lh } , redirect: "manual" }); } // gettoken?corpid=… (WeCom)
      else if ((login as any).body_format === "form") resp = await this.fetcher(url, { method: m, headers: { "Content-Type": "application/x-www-form-urlencoded", Accept: "application/json", "User-Agent": this.userAgent, ...lh }, body: new URLSearchParams(body as Record<string, string>).toString() , redirect: "manual" });
      else resp = await this.fetcher(url, { method: m, headers: { "Content-Type": "application/json", Accept: "application/json", "User-Agent": this.userAgent, ...lh }, body: JSON.stringify(body) , redirect: "manual" });
    } else if (a.type === "oauth2_client_credentials" || a.type === "oauth2_refresh_token") {
      const cid = this.creds[a.client_id_field ?? "client_id"]; const secret = this.creds[a.client_secret_field ?? "client_secret"] ?? "";
      const form = new URLSearchParams(a.type === "oauth2_refresh_token"
        ? { grant_type: "refresh_token", refresh_token: this.creds[a.refresh_token_field ?? "refresh_token"] } // minted from the refresh token the user obtained once
        : { grant_type: a.grant ?? "client_credentials" });
      if (a.scope) form.set("scope", a.scope);
      for (const [k, v] of Object.entries(a.token_params ?? {})) form.set(k, typeof v === "string" && v.includes("{") ? this.render(v, nowCtx) : v);
      const headers: Record<string, string> = { "Content-Type": "application/x-www-form-urlencoded", Accept: "application/json", "User-Agent": this.userAgent,
        ...Object.fromEntries(Object.entries((a as any).token_headers ?? {}).map(([h, t]) => [h, this.render(String(t), nowCtx)])) };
      if ((a.client_auth ?? "basic") === "body") { form.set("client_id", cid); if (secret) form.set("client_secret", secret); }
      else { headers.Authorization = "Basic " + Buffer.from(`${cid}:${secret}`).toString("base64"); registerSecret(headers.Authorization.slice(6)); }
      const renames: Record<string, string | null> = (a as any).token_fields ?? {};
      if (Object.keys(renames).length) { // platforms that name the grant fields differently (app_id/secret, client_key)
        const entries = [...form.entries()]; for (const [k] of entries) form.delete(k);
        for (const [k, v] of entries) { const nk = k in renames ? renames[k] : k; if (nk !== null) form.set(nk, v); }
      }
      let tokenUrl = this.fillPath(a.token_url!); // per-install hosts / instances in the token URL
      const aa: any = a;
      if (aa.token_sign || aa.token_query || aa.token_body_extra) { // signed token requests (Shopee)
        const tctx: Record<string, string> = { ...nowCtx, path: new URL(tokenUrl).pathname, access_token: String(this.token ?? "") };
        if (aa.token_sign) tctx.signature = Transport.encode(this.digest(aa.token_sign, this.render(aa.token_sign.payload, tctx), this.keyBytes(aa.token_sign)), aa.token_sign.encoding, aa.token_sign.case);
        for (const [k, v] of Object.entries(aa.token_body_extra ?? {})) { const asInt = typeof v === "string" && v.startsWith("int:"); const r = this.render(asInt ? String(v).slice(4) : String(v), tctx); form.set(k, r); if (asInt) (form as any).__ints = { ...((form as any).__ints ?? {}), [k]: true }; }
        if (aa.token_query) tokenUrl += (tokenUrl.includes("?") ? "&" : "?") + Object.entries(aa.token_query).map(([k, v]) => `${k}=${encodeURIComponent(this.render(String(v), tctx))}`).join("&");
      }
      if (((a as any).token_method ?? "POST").toUpperCase() === "GET") { delete headers["Content-Type"]; resp = await this.fetcher(`${tokenUrl}${tokenUrl.includes("?") ? "&" : "?"}${form.toString()}`, { method: "GET", headers , redirect: "manual" }); }
      else if ((a as any).token_body === "json") {
        headers["Content-Type"] = "application/json";
        const ints = (form as any).__ints ?? {}; const obj: Record<string, unknown> = {};
        for (const [k, v] of form.entries()) obj[k] = ints[k] && /^-?\d+$/.test(v) ? Number(v) : v; // "int:{@partner_id}" → JSON integer
        resp = await this.fetcher(tokenUrl, { method: "POST", headers, body: JSON.stringify(obj) , redirect: "manual" });
      }
      else resp = await this.fetcher(tokenUrl, { method: "POST", headers, body: form.toString() , redirect: "manual" });
    } else throw new InvalidInput(`no token flow for auth type ${a.type}`);
    const text = await resp.text();
    if ([400, 401, 403].includes(resp.status)) throw new AuthError(scrub(`token request refused (${resp.status}): ${text.slice(0, 200)}`), { status: resp.status });
    if (resp.status >= 400) throw new PlatformError(scrub(`token request failed (${resp.status})`), { status: resp.status });
    let payload: any = {}; let token: any;
    if ((a as any).token_from_cookie === "*") { // replay every login cookie
      const sc = resp.headers.get("set-cookie") ?? "";
      token = sc.split(/,(?=\s*[A-Za-z0-9_.-]+=)/).map((c: string) => c.trim().split(";")[0]).filter(Boolean).join("; ") || undefined;
    } else if ((a as any).token_from_cookie) { // sessions handed back as Set-Cookie
      const sc = resp.headers.get("set-cookie") ?? "";
      const m = new RegExp(`(?:^|[,;]\\s*)${(a as any).token_from_cookie}=([^;,]+)`).exec(sc); token = m ? m[1] : undefined;
    } else if ((a as any).token_from_header) token = resp.headers.get((a as any).token_from_header); // tokens handed back in a response header
    else {
      const t = text.trim();
      payload = t.startsWith("{") || t.startsWith("[") ? JSON.parse(t) : t.startsWith("<") ? xmlToObj(t) : {};
      token = payload;
      for (const part of (a.token_path ?? "access_token").split(".")) token = token && typeof token === "object" ? token[part] : undefined;
    }
    if (typeof token !== "string" || !token) throw new AuthError("token response carried no token");
    let ttl: any = payload; for (const part of (a.expires_path ?? "expires_in").split(".")) ttl = ttl && typeof ttl === "object" ? ttl[part] : undefined; // nested expiry: data.expires_in
    registerSecret(token);
    let rotated: any = payload; for (const part of ((a as any).refresh_token_path ?? "refresh_token").split(".")) rotated = rotated && typeof rotated === "object" ? rotated[part] : undefined;
    if (a.type === "oauth2_refresh_token" && typeof rotated === "string" && rotated) this.storeRotatedRefreshToken(rotated); // single-use refresh tokens (nested: data.refresh_token)
    this.token = token;
    this.tokenExpires = Date.now() + (typeof ttl === "number" && ttl > 60 ? (ttl - 30) * 1000 : (a.token_ttl_seconds ?? 1800) * 1000);
    return token;
  }
  /** Opt-in persistence of rotated refresh tokens: PLATFORM_MCP_STATE_DIR/<platform>.json (0600). */
  private stateFile(): string | undefined {
    const root = process.env.PLATFORM_MCP_STATE_DIR, key = (this.auth as any).state_key;
    return root && key ? `${root.replace(/\/+$/, "")}/${key}.json` : undefined;
  }
  private loadRotatedRefreshToken(): void {
    if (this.auth.type !== "oauth2_refresh_token") return;
    const file = this.stateFile();
    if (!file || !fs.existsSync(file)) return;
    try {
      const saved = JSON.parse(fs.readFileSync(file, "utf8")).refresh_token;
      if (typeof saved === "string" && saved) { this.creds[this.auth.refresh_token_field ?? "refresh_token"] = saved; registerSecret(saved); }
    } catch { /* unreadable state: keep the configured token */ }
  }
  private storeRotatedRefreshToken(value: string): void {
    const field = this.auth.refresh_token_field ?? "refresh_token";
    if (this.creds[field] === value) return;
    registerSecret(value);
    this.creds[field] = value; // the next refresh in this process uses the new one
    const file = this.stateFile();
    if (!file) return;
    const dir = file.replace(/\/[^/]+$/, "");
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
    // a fresh, exclusively created temp file (0600, never a planted symlink), then an atomic rename
    const tmp = `${dir}/.${file.slice(dir.length + 1)}.${process.pid}.${crypto.randomBytes(6).toString("hex")}.tmp`;
    try {
      fs.writeFileSync(tmp, JSON.stringify({ refresh_token: value }), { mode: 0o600, flag: "wx" });
      fs.chmodSync(tmp, 0o600);
      fs.renameSync(tmp, file);
    } catch (e) { try { fs.unlinkSync(tmp); } catch { /* already gone */ } throw e; }
  }
  private render(template: string, ctx: Record<string, string>): string {
    return template.replace(/\{(@?[A-Za-z_][A-Za-z0-9_]*)\}/g, (m, k: string) => (k.startsWith("@") ? this.creds[k.slice(1)] ?? "" : ctx[k] ?? m));
  }
  /** auth.sign: HMAC request signing (Binance, Bybit, OKX, Coupang...). Appends to `pairs` in place; returns headers. */
  private static encode(digest: Buffer, encoding?: string, kase?: string): string {
    let out: string;
    if (encoding === "base64") out = digest.toString("base64");
    else if (encoding === "base64url") out = digest.toString("base64url");
    else if (encoding === "base64_hex") out = Buffer.from(digest.toString("hex")).toString("base64"); // Base64 of the hex digest text (SHEIN)
    else out = digest.toString("hex");
    return kase === "upper" ? out.toUpperCase() : out;
  }
  private keyBytes(spec: any, field?: string): Buffer {
    const raw = this.creds[field ?? spec.key_field ?? "api_secret"] ?? "";
    if (spec.key_encoding === "base64") return Buffer.from(raw, "base64");
    if (spec.key_encoding === "base64url") return Buffer.from(raw, "base64url");
    if (spec.key_encoding === "hex") return Buffer.from(raw, "hex");
    return Buffer.from(raw);
  }
  private digest(spec: any, payload: string, secret: Buffer): Buffer {
    const algo = spec.algorithm ?? "sha256";
    return (spec.mode ?? "hmac") === "hash" ? crypto.createHash(algo).update(payload).digest() : crypto.createHmac(algo, secret).update(payload).digest();
  }
  /** auth.cookies {name: template}: cookie-borne sessions (token, timestamp, unique id per request). */
  private cookieHeader(): Record<string, string> {
    const tpl = (this.auth as any).cookies;
    if (!tpl) return (this.auth as any).token_from_cookie === "*" && this.token ? { Cookie: this.token } : {};
    const ctx: Record<string, string> = { access_token: String(this.token ?? ""), timestamp: String(Date.now()), timestamp_s: String(Math.floor(Date.now() / 1000)), nonce: crypto.randomUUID().replace(/-/g, "") };
    return { Cookie: Object.entries(tpl).map(([k, v]) => `${k}=${this.render(String(v), ctx)}`).join("; ") };
  }
  /** auth.sign — same modes, placeholders and outputs as the Python runtime's _sign. Appends to `pairs`
   * in place; returns headers and (for body_field signing) the signature. */
  private sign(method: string, base: string, pairs: string[], bodyStr: string, bodyObj?: Record<string, unknown>, formKv?: [string, string][]): { headers: Record<string, string>; bodySig?: string } {
    const spec = (this.auth as any).sign;
    if (!spec) return { headers: {} };
    const now = Date.now(); const d = new Date(now); const iso = d.toISOString();
    const ctx: Record<string, string> = { timestamp: String(now), timestamp_s: String(Math.floor(now / 1000)), timestamp_iso: iso,
      datetime_compact: iso.slice(2, 19).replace(/[-:]/g, "") + "Z", amz_date: iso.slice(0, 19).replace(/[-:]/g, "") + "Z", date: iso.slice(0, 10).replace(/-/g, ""),
      nonce: crypto.randomUUID().replace(/-/g, ""), access_token: String(this.token ?? "") };
    if (spec.timestamp_format) {
      const off: string = spec.timestamp_offset ?? "+00:00"; const sg = off[0] === "-" ? -1 : 1;
      const local = new Date(now + sg * (Number(off.slice(1, 3)) * 60 + Number(off.slice(4, 6))) * 60000);
      const p2 = (n: number) => String(n).padStart(2, "0");
      const map: Record<string, string> = { "%Y": String(local.getUTCFullYear()), "%y": p2(local.getUTCFullYear() % 100), "%m": p2(local.getUTCMonth() + 1), "%d": p2(local.getUTCDate()), "%H": p2(local.getUTCHours()), "%M": p2(local.getUTCMinutes()), "%S": p2(local.getUTCSeconds()) };
      ctx.timestamp_fmt = String(spec.timestamp_format).replace(/%[YymdHMS]/g, (t: string) => map[t]);
    }
    const enc = (x: string) => encodeURIComponent(x).replace(/[!'()*]/g, (c) => "%" + c.charCodeAt(0).toString(16).toUpperCase());
    if (spec.timestamp_param) pairs.push(`${spec.timestamp_param}=${enc(ctx[spec.timestamp_value ?? "timestamp"])}`);
    for (const [k, v] of Object.entries(spec.params ?? {})) pairs.push(`${k}=${enc(this.render(String(v), ctx))}`);
    const query = pairs.join("&");
    const kv = pairs.filter(Boolean).map((p) => { const i = p.indexOf("="); return [decodeURIComponent(i < 0 ? p : p.slice(0, i)), i < 0 ? "" : decodeURIComponent(p.slice(i + 1))]; })
      .sort((x, y) => (x[0] < y[0] ? -1 : x[0] > y[0] ? 1 : x[1] < y[1] ? -1 : x[1] > y[1] ? 1 : 0))
      .filter(([k]) => !(spec.exclude ?? []).includes(k)); // params the platform leaves out of the signature
    let path = new URL(base).pathname;
    if (spec.path_strip && path.startsWith(spec.path_strip)) path = path.slice(spec.path_strip.length) || "/";
    const bodyKv = bodyObj && typeof bodyObj === "object" && !Array.isArray(bodyObj)
      ? Object.entries(bodyObj).filter(([, v]) => v !== undefined && v !== null).map(([k, v]) => [k, typeof v === "string" ? v : JSON.stringify(v)] as [string, string]).sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0)) : [];
    Object.assign(ctx, { method: method.toUpperCase(), path, query, query_q: query ? "?" + query : "", body: bodyStr,
      sorted_params: kv.map(([k, v]) => k + v).join(""), sorted_query: kv.map(([k, v]) => `${k}=${v}`).join("&"),
      sorted_values: kv.map(([, v]) => v).join(""), sorted_kv: kv.map(([k, v]) => `${k}=${v}`).join(""), sorted_body: bodyKv.map(([k, v]) => k + v).join("") });
    for (const step of spec.pre ?? []) ctx[step.name] = Transport.encode(this.digest(step, this.render(step.payload, ctx), this.keyBytes(step)), step.encoding, step.case); // nested digests
    const mode = spec.mode ?? "hmac"; let signature: string; let extra: Record<string, string> = {};
    if (mode === "jwt_hs256" || mode === "jwt_rs256") {
      const claims: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(spec.claims ?? {})) {
        if (typeof v === "string" && /^\+\d+$/.test(v)) claims[k] = Number(ctx.timestamp_s) + Number(v.slice(1)); // "+300" → expiry 5 minutes from now
        else { const r = this.render(String(v), ctx); claims[k] = /^\d+$/.test(r) && ["{timestamp}", "{timestamp_s}"].includes(String(v)) ? Number(r) : r; }
      }
      const b64 = (o: unknown) => Buffer.from(JSON.stringify(o)).toString("base64url");
      const hdr = Object.fromEntries(Object.entries(spec.jwt_header ?? {}).map(([k, v]) => [k, this.render(String(v), ctx)]));
      const head = b64({ alg: mode === "jwt_hs256" ? "HS256" : "RS256", typ: "JWT", ...hdr }) + "." + b64(claims);
      const sig = mode === "jwt_hs256"
        ? crypto.createHmac("sha256", spec.key_encoding ? this.keyBytes(spec) : (this.creds[spec.key_field ?? "api_secret"] ?? "").replace(/\\n/g, "\n")).update(head).digest("base64url")
        : crypto.createSign("RSA-SHA256").update(head).sign((this.creds[spec.key_field ?? "api_secret"] ?? "").replace(/\\n/g, "\n"), "base64url");
      signature = `${head}.${sig}`;
    } else if (mode === "rsa_sha256") {
      const pem = (this.creds[spec.key_field ?? "private_key"] ?? "").replace(/\\n/g, "\n");
      signature = Transport.encode(crypto.createSign("RSA-SHA256").update(this.render(spec.payload, ctx)).sign(pem), spec.encoding ?? "base64", spec.case);
    } else if (mode === "aws_sigv4") {
      const region = this.render(spec.region ?? "{@region}", ctx); const service = spec.service; const u = new URL(base);
      const q = (x: string) => encodeURIComponent(x).replace(/[!'()*]/g, (c) => "%" + c.charCodeAt(0).toString(16).toUpperCase());
      const canonQ = kv.map(([k, v]) => `${q(k)}=${q(v)}`).join("&");
      const payloadHash = crypto.createHash("sha256").update(bodyStr ?? "").digest("hex");
      const signed: Record<string, string> = { host: u.host, "x-amz-date": ctx.amz_date };
      const tok = this.creds[spec.session_token_field ?? "session_token"]; if (tok) signed["x-amz-security-token"] = tok;
      const names = Object.keys(signed).sort();
      const canonPath = (u.pathname || "/").split("/").map((seg) => q(decodeURIComponent(seg))).join("/");
      const canonical = [method.toUpperCase(), canonPath, canonQ, names.map((n) => `${n}:${signed[n]}\n`).join(""), names.join(";"), payloadHash].join("\n");
      const scope = `${ctx.date}/${region}/${service}/aws4_request`;
      const toSign = ["AWS4-HMAC-SHA256", ctx.amz_date, scope, crypto.createHash("sha256").update(canonical).digest("hex")].join("\n");
      let k: Buffer = Buffer.from("AWS4" + (this.creds[spec.secret_key_field ?? "secret_access_key"] ?? ""));
      for (const part of [ctx.date, region, service, "aws4_request"]) k = crypto.createHmac("sha256", k).update(part).digest();
      signature = crypto.createHmac("sha256", k).update(toSign).digest("hex");
      extra = { "X-Amz-Date": ctx.amz_date, Authorization: `AWS4-HMAC-SHA256 Credential=${this.creds[spec.access_key_field ?? "access_key_id"] ?? ""}/${scope}, SignedHeaders=${names.join(";")}, Signature=${signature}` };
      if (tok) extra["X-Amz-Security-Token"] = tok;
    } else if (mode === "oauth1") {
      const e = (x: unknown) => encodeURIComponent(String(x)).replace(/[!'()*]/g, (c) => "%" + c.charCodeAt(0).toString(16).toUpperCase()); // RFC 5849
      const oauth: Record<string, string> = { oauth_consumer_key: this.creds[spec.consumer_key_field ?? "consumer_key"] ?? "", oauth_nonce: ctx.nonce, oauth_signature_method: "HMAC-SHA1", oauth_timestamp: ctx.timestamp_s, oauth_version: "1.0" };
      const tk = this.creds[spec.token_field ?? "access_token"]; if (tk) oauth.oauth_token = tk;
      // RFC 5849 3.4.1.3.1: form-encoded body parameters are signed with the query and oauth_* parameters
      const all = [...kv.map(([k, v]) => [e(k), e(v)]), ...(formKv ?? []).map(([k, v]) => [e(k), e(v)]), ...Object.entries(oauth).map(([k, v]) => [e(k), e(v)])].sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : a[1] < b[1] ? -1 : a[1] > b[1] ? 1 : 0));
      const baseStr = [method.toUpperCase(), e(base.split("?")[0]), e(all.map(([k, v]) => `${k}=${v}`).join("&"))].join("&");
      const key = `${e(this.creds[spec.consumer_secret_field ?? "consumer_secret"] ?? "")}&${e(this.creds[spec.token_secret_field ?? "access_token_secret"] ?? "")}`;
      signature = crypto.createHmac("sha1", key).update(baseStr).digest("base64");
      oauth.oauth_signature = signature;
      extra = { Authorization: "OAuth " + Object.keys(oauth).sort().map((k) => `${e(k)}="${e(oauth[k])}"`).join(", ") };
    } else {
      signature = Transport.encode(this.digest(spec, this.render(spec.payload, ctx), this.keyBytes(spec)), spec.encoding, spec.case);
    }
    ctx.signature = signature;
    const headers = { ...extra, ...Object.fromEntries(Object.entries(spec.headers ?? {}).map(([h, t]) => [h, this.render(String(t), ctx)])) };
    if (spec.body_field) return { headers, bodySig: signature };
    if (spec.signature_param) pairs.push(`${spec.signature_param}=${encodeURIComponent(signature)}`);
    return { headers };
  }
  private async dynamicHeaders(force = false): Promise<Record<string, string>> {
    if (!["session", "oauth2_client_credentials", "oauth2_refresh_token"].includes(this.auth.type ?? "")) return {};
    if (force || !this.token || Date.now() >= this.tokenExpires) await this.acquireToken();
    if ((this.auth as any).token_param || (this.auth as any).header === "") return {}; // sent as a query parameter or only via cookies instead
    return { [this.auth.header ?? "Authorization"]: (this.auth.prefix ?? "Bearer ") + this.token };
  }
  /** Short-lived bounded cache of successful bodies for tools that page a whole collection locally (see ResponseCache). */
  public cache = new ResponseCache();
  /** Resolver for the download guard (netguard.ts); tests inject one. */
  public resolveHost: Resolver = defaultResolver;
  /** The pinned GET used for downloads on the real network (netguard.ts); tests replace it to observe the address. */
  public pinnedGet = pinnedGet;
  /** A multipart `file:<arg>` part (http.py _download): every hop must resolve to public addresses only (redirects
   *  followed one at a time, at most 5) and the body is capped at PLATFORM_MCP_MAX_DOWNLOAD_MB (default 50). */
  private async download(url: string, field: string): Promise<[Buffer, string]> {
    const mb = Number(process.env.PLATFORM_MCP_MAX_DOWNLOAD_MB ?? 50);
    const cap = Math.trunc((Number.isFinite(mb) ? mb : 50) * 1_000_000);
    const tooLarge = () => new InvalidInput(`${field}: the file is larger than PLATFORM_MCP_MAX_DOWNLOAD_MB`);
    for (let hop = 0; hop < 6; hop++) {
      const vetted = await checkUrl(url, this.resolveHost, `the ${field} URL`);
      const hdrs = { "User-Agent": this.userAgent, Accept: "*/*" };
      // the real network path connects to the vetted address (no second DNS answer); an injected fetcher (tests) is used as is
      const got: any = vetted && this.fetcher === (globalThis.fetch as unknown) ? await this.pinnedGet(url, pick(vetted), hdrs)
        : await this.fetcher(url, { method: "GET", headers: hdrs, redirect: "manual" });
      const loc = got.headers.get("location");
      if ([301, 302, 303, 307, 308].includes(got.status) && loc) { got.destroy?.(); url = new URL(loc, url).toString(); continue; }
      if (got.status >= 400) { got.destroy?.(); throw new InvalidInput(`could not download ${field} from the given URL (${got.status})`); }
      const size = got.headers.get("content-length");
      if (size && /^\d+$/.test(size) && Number(size) > cap) throw tooLarge();
      let bytes: Buffer;
      if (got.body && typeof got.body[Symbol.asyncIterator] === "function" && typeof got.body.getReader !== "function") { // node:http response
        const chunks: Buffer[] = []; let n = 0;
        for await (const value of got.body) { n += value.length; if (n > cap) { got.destroy?.(); throw tooLarge(); } chunks.push(Buffer.from(value)); }
        bytes = Buffer.concat(chunks);
      } else if (got.body && typeof got.body.getReader === "function") {
        const reader = got.body.getReader(); const chunks: Buffer[] = []; let n = 0;
        for (;;) { const { done, value } = await reader.read(); if (done) break; n += value.length; if (n > cap) { await reader.cancel(); throw tooLarge(); } chunks.push(Buffer.from(value)); }
        bytes = Buffer.concat(chunks);
      } else bytes = got.arrayBuffer ? Buffer.from(await got.arrayBuffer()) : Buffer.from(await got.text());
      if (bytes.length > cap) throw tooLarge();
      return [bytes, got.headers.get("content-type") ?? "application/octet-stream"];
    }
    throw new InvalidInput(`could not download ${field}: too many redirects`);
  }
  async request(method: string, path: string, params: Record<string, unknown> = {}, json?: any, form = false, toolHeaders: Record<string, string> = {}, querySafe = "", doSign = true, xmlRoot?: string, multipart = false, cacheTtl?: number, wantHeaders = false, csv?: { delimiter?: string; skip_lines?: number }, read?: boolean): Promise<unknown> {
    let cacheKey: string | undefined;
    if (cacheTtl && !multipart && this.cache.enabled) { // paging through a whole collection reuses one download for cacheTtl seconds
      cacheKey = stableJson([method.toUpperCase(), path, Object.entries(params).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)), json ?? null]);
      const hit = this.cache.get(cacheKey);
      if (hit) { const data = this.decode(hit[0], hit[1], method, csv); return wantHeaders ? { data, headers: hit[2] ?? {} } : data; }
    }
    await this.bucket.take();
    const downloads: Record<string, [Buffer, string]> = {}; // multipart files are fetched once, even when the request is sent twice
    const original = json;
    // build the whole request from scratch (token, URL, query, body, signature) and send it; after a 401 the token
    // is minted again and the request REBUILT, since the token may sit in the query, path, body, a cookie or a signature
    const send = async (force: boolean) => {
      let json = original;
      const dyn = await this.dynamicHeaders(force); // mint first: the token may also go into the path or body
      const full = this.fillPath(path.startsWith("http") ? path : this.baseUrl + path);
      if ((this.auth as any).token_body_path && this.token && json && typeof json === "object" && !Array.isArray(json)) {
        json = JSON.parse(JSON.stringify(json)); const parts = String((this.auth as any).token_body_path).split("."); let cur: any = json;
        for (const part of parts.slice(0, -1)) cur = cur[part] ??= {};
        cur[parts[parts.length - 1]] = this.token; // token inside the JSON body (Baidu header.accessToken)
      }
      // keep a query string written into the path and encode ourselves, so `querySafe` characters (Rest.li `(),:`) stay literal
      const [base, inline] = [full.split("?")[0], full.includes("?") ? full.slice(full.indexOf("?") + 1) : ""];
      const enc = (x: string, safe: string) => [...safe].reduce((acc, ch) => acc.split(encodeURIComponent(ch)).join(ch), encodeURIComponent(x));
      const pairs: string[] = inline ? [inline] : [];
      const add = (k: string, v: unknown) => { for (const item of Array.isArray(v) ? v : [v]) pairs.push(`${enc(k, querySafe + "[]")}=${enc(String(item), querySafe)}`); };
      for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== "") add(k, v);
      for (const [k, v] of Object.entries(authParams(this.auth, this.creds))) add(k, v);
      if ((this.auth as any).token_param && this.token) add((this.auth as any).token_param, this.token);
      const headers: Record<string, string> = { "User-Agent": this.userAgent, Accept: "application/json", ...this.fixedHeaders, ...toolHeaders, ...authHeaders(this.auth, this.creds), ...dyn };
      Object.assign(headers, this.cookieHeader());
      const hasCT = Object.keys(headers).some((h) => h.toLowerCase() === "content-type"); // adapter.headers may pin a vendor media type
      if (json && !hasCT && !multipart) headers["Content-Type"] = xmlRoot ? "application/xml" : form ? "application/x-www-form-urlencoded" : "application/json";
      const sspec = (this.auth as any).sign ?? {};
      if (doSign && sspec.body_field && json && typeof json === "object" && !Array.isArray(json) && !xmlRoot && !form) {
        // the signature is computed over the body's own fields and travels inside the body (Temu)
        json = { ...json, [sspec.body_field]: this.sign(method, base, [...pairs], "", json).bodySig };
      }
      let body: any = json ? (xmlRoot ? objToXml(xmlRoot, json) : form ? formBody(json) : JSON.stringify(json)) : undefined;
      if (multipart && json && typeof json === "object") {
        // multipart/form-data: text fields as-is, `file:<url>` fields downloaded (guarded) and attached; fetch sets the boundary
        const fd = new FormData();
        for (const [k, v] of Object.entries(json as Record<string, any>)) {
          if (v && typeof v === "object" && "_json_part" in v) { fd.append(k, new Blob([JSON.stringify(v._json_part)], { type: "application/json" })); continue; }
          if (v && typeof v === "object" && "_file_url" in v) {
            downloads[k] ??= await this.download(String(v._file_url), k);
            const [bytes, ctype] = downloads[k];
            const name = String(v._file_url).split("?")[0].replace(/\/+$/, "").split("/").pop() || k;
            fd.append(k, new Blob([new Uint8Array(bytes)], { type: ctype }), name);
          } else fd.append(k, v === true ? "true" : v === false ? "false" : String(v));
        }
        body = fd;
        for (const h of Object.keys(headers)) if (h.toLowerCase() === "content-type") delete headers[h];
      }
      const formKv = form && json && typeof json === "object" && !Array.isArray(json) ? [...new URLSearchParams(formBody(json as Record<string, unknown>)).entries()] as [string, string][] : undefined;
      if (doSign && !sspec.body_field) Object.assign(headers, this.sign(method, base, pairs, body ?? "", json && typeof json === "object" && !Array.isArray(json) ? json : undefined, formKv).headers); // tool `sign: false`: public endpoints that reject extra params
      const url = base + (pairs.length ? "?" + pairs.join("&") : "");
      // redirects are followed within the same origin only (follow): a cross-origin redirect would carry API-key headers and signatures elsewhere
      try { return await this.follow(method, url, headers, body); }
      catch (e) { if (e instanceof PlatformError) throw e; throw new PlatformError(scrub(`network error: ${(e as Error).name}`)); }
    };
    let resp = await send(false);
    if (resp.status === 401 && ["session", "oauth2_client_credentials", "oauth2_refresh_token"].includes(this.auth.type ?? "")) resp = await send(true);
    const text = await bodyText(resp);
    if (resp.status >= 400) {
      // the kind tells the model whom to act on: its arguments (invalid_input, not_found, conflict), the credentials, time or the platform
      const kind = classify(resp.status, text, { method: read === undefined ? method : read ? "GET" : method, rules: this.errorKinds }); // a read verb is a read whatever its HTTP method
      const ra = resp.headers.get("Retry-After");
      if (kind === RateLimited) throw new RateLimited("rate limited by the platform" + (resp.status !== 429 ? ` (${resp.status}): ${scrub(text.slice(0, 200))}` : ""), { retryAfter: ra && /^\d+$/.test(ra) ? Number(ra) : undefined, status: resp.status });
      throw new kind(scrub(messageFor(kind, resp.status, text)), { status: resp.status });
    }
    const ctype = resp.headers.get("content-type") ?? "";
    const data = this.decode(text, ctype, method, csv);
    const respHeaders = headerMap(resp.headers);
    if (cacheKey !== undefined && resp.status < 300) this.cache.put(cacheKey, text, ctype, cacheTtl!, respHeaders); // only successes (envelope failures threw above)
    return wantHeaders ? { data, headers: respHeaders } : data;
  }
  /** One request, following redirects as Python's runtime does: only within the same origin (a cross-origin Location
   *  is refused so no credential is replayed to another host), 303 (and 301/302 after a non-GET) as a GET without a
   *  body, at most 5 hops; a 3xx that cannot be followed is an error, never an empty success. */
  private async follow(method: string, url: string, headers: Record<string, string>, body: any): Promise<any> {
    let resp: any = await this.fetcher(url, { method, headers, body, redirect: "manual" } as any);
    let hops = 0;
    while ([301, 302, 303, 307, 308].includes(resp.status) && resp.headers.get("location")) {
      const target = new URL(resp.headers.get("location")!, url);
      const from = new URL(url);
      if (target.protocol !== from.protocol || target.host !== from.host) throw new PlatformError(scrub(`the platform redirected (${resp.status}) to another host, ${target.host}; not followed so no credential leaves ${from.host}`), { status: resp.status });
      if (++hops > 5) throw new PlatformError(`too many redirects (${resp.status})`, { status: resp.status });
      if (resp.status === 303 || ([301, 302].includes(resp.status) && !["GET", "HEAD"].includes(method.toUpperCase()))) {
        method = "GET"; body = undefined;
        headers = Object.fromEntries(Object.entries(headers).filter(([k]) => k.toLowerCase() !== "content-type"));
      }
      url = target.toString();
      resp = await this.fetcher(url, { method, headers, body, redirect: "manual" } as any);
    }
    if (resp.status >= 300 && resp.status < 400) throw new PlatformError(`the platform answered ${resp.status} without a redirect that can be followed`, { status: resp.status });
    return resp;
  }
  /** Parse a successful body (JSON, XML, CSV or text) and apply the envelope rules. */
  private decode(text: string, ctype: string, method: string, csv?: { delimiter?: string; skip_lines?: number }): unknown {
    if (!text.trim()) return {}; // 204 No Content and empty 200 bodies
    if (ctype.includes("csv") || csv) { // CSV → {rows: [{header: value}]}; a tool's `csv` forces it whatever the content type
      let body = text.replace(/^\ufeff/, "");
      if (csv?.skip_lines) body = body.split(/\r\n|\n|\r/).slice(Number(csv.skip_lines)).join("\n");
      return { rows: parseCsv(body, csv?.delimiter || ",") };
    }
    if (ctype.toLowerCase().includes("text/html") || /^\s*<(?:!doctype\s+html|html[\s>])/i.test(text.slice(0, 200))) return unparsed(text, ctype || "text/html"); // an HTML page is never an API record, even when it parses as XML
    const isXml = ctype.includes("xml") || text.trimStart().startsWith("<");
    if (isXml || ctype.includes("json") || /^[\[{]/.test(text.trim())) {
      let data: any;
      try { data = isXml && text.trimStart().startsWith("<") ? xmlToObj(text) : JSON.parse(text); } catch { return unparsed(text, ctype); }
      const env = this.envelope;
      const digPath = (path: string): any => dig(data, path);
      let notice: string | undefined; let present = false;
      for (const path of ((env as any).fail_if_present ?? []) as string[]) {
        // an error list/object that is present and non-empty means failure (Kraken {"error": ["EQuery:…"]}, GraphQL {"errors": [...]})
        const found = digPath(path);
        const empty = found === undefined || found === null || found === "" || (Array.isArray(found) && found.length === 0) || (typeof found === "object" && !Array.isArray(found) && Object.keys(found).length === 0);
        if (!empty) {
          let detail = env.error_field ? digPath(env.error_field) : undefined;
          if (detail === undefined || detail === null || detail === "") detail = found;
          notice = jsonText(detail);
          present = true;
          break;
        }
      } // fail_when: a notice served as a normal 200 document (a feed whose only item says 'Too Many Requests', a decoder whose record comes back empty)
      for (const [path, value] of Object.entries((env as any).fail_when ?? {})) {
        // `null` matches an explicit null only, never an absent path (a list answer has no data.last)
        const [found, got] = digFound(data, path);
        if (!present && found && got === value) {
          const detail = env.error_field ? digPath(env.error_field) : undefined;
          notice = detail !== undefined && detail !== null && detail !== "" ? jsonText(detail) : value === null ? `${path} is null` : jsonText(value);
        }
      }
      if (notice !== undefined || (env.ok_field && data && typeof data === "object" && env.ok_field in data && ("ok_value" in env ? !(Array.isArray((env as any).ok_value) ? (env as any).ok_value : [(env as any).ok_value]).includes(data[env.ok_field]) : !data[env.ok_field]))) { // ok_value: code 0 = success
        const detail = data && typeof data === "object" && !Array.isArray(data) ? digPath(env.error_field ?? "error") : undefined;
        const msg = notice ?? jsonText(detail ?? "request failed");
        const kind = classify(200, msg, { method, rules: this.errorKinds, envelope: true });
        throw new kind(kind === RateLimited || kind === AuthError ? scrub(msg) : scrub(msg).slice(0, 300), { status: 200 });
      }
      return data;
    }
    return unparsed(text, ctype);
  }
}
