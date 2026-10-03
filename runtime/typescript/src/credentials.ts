import { AuthError } from "./errors.js";

export function envName(platformId: string, field: string): string {
  return `PLATFORM_MCP_${platformId.toUpperCase()}_${field.toUpperCase()}`;
}

export interface AuthField { name: string; required?: boolean; help?: string }

export function resolve(platformId: string, auth: { fields?: (AuthField | string)[] }, configFields: (AuthField | string)[] = []): Record<string, string> {
  const out: Record<string, string> = {};
  const missing: string[] = [];
  for (const f of [...(auth.fields ?? []), ...configFields]) {
    const name = typeof f === "string" ? f : f.name;
    const required = typeof f === "string" ? true : f.required ?? true;
    const value = process.env[envName(platformId, name)];
    if (value) out[name] = value;
    else if (required) missing.push(envName(platformId, name));
  }
  if (missing.length) throw new AuthError("missing credentials; set " + missing.join(", "));
  return out;
}

const SECRET_RE = /(["']?)((?:api[_-]?key|access[_-]?token|refresh[_-]?token|id[_-]?token|client[_-]?secret|token|secret|password|authorization|bearer|jwt))\1(\s*[:=]\s*)((?:bearer|basic|token|bot|oauth|digest)\s+(?=[^\s"']))?("[^"]*"|'[^']*'|\S+)/gi;
const KNOWN = new Set<string>();
/** Python's urllib.parse.quote(value, safe=safe): RFC 3986 unreserved characters and `safe` stay literal. */
function quote(value: string, safe: string): string {
  return encodeURIComponent(value).replace(/[!'()*]/g, (c) => "%" + c.charCodeAt(0).toString(16).toUpperCase()).replace(/%2F/g, safe.includes("/") ? "/" : "%2F");
}
/** Remember a credential or minted token so it is redacted wherever it appears, including error bodies that echo it,
 *  URL-encoded (an echoed query string or form body) or form-encoded (spaces as '+'), as the Python runtime does. */
export function registerSecret(value: unknown): void {
  if (typeof value !== "string" || value.length < 6) return;
  for (const v of [value, quote(value, ""), quote(value, "/"), quote(value, "").replace(/%20/g, "+")]) KNOWN.add(v);
}
export function scrub(text: string): string {
  let out = text ?? "";
  for (const v of [...KNOWN].sort((a, b) => b.length - a.length)) if (out.includes(v)) out = out.split(v).join("<redacted>");
  return out.replace(SECRET_RE, (_m, q, key, sep, scheme) => `${q}${key}${q}${sep}${scheme ?? ""}<redacted>`);
}
