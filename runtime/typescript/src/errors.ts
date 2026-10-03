/** Error family shared by every server. API failures become `isError` results, never protocol errors. */
export class PlatformError extends Error {
  kind = "upstream_error";
  retryAfter?: number;
  status?: number;
  constructor(message: string, opts: { retryAfter?: number; status?: number } = {}) {
    super(message);
    this.retryAfter = opts.retryAfter;
    this.status = opts.status;
  }
  payload(): Record<string, unknown> {
    const out: Record<string, unknown> = { error: this.kind, message: this.message };
    if (this.retryAfter !== undefined) out.retry_after_seconds = this.retryAfter;
    if (this.status !== undefined) out.http_status = this.status;
    return out;
  }
}
export class AuthError extends PlatformError { kind = "auth_error"; }
export class RateLimited extends PlatformError { kind = "rate_limited"; }
export class NotSupported extends PlatformError { kind = "not_supported"; }
export class InvalidInput extends PlatformError { kind = "invalid_input"; }
export class NotFound extends PlatformError { kind = "not_found"; }
export class Conflict extends PlatformError { kind = "conflict"; }

type ErrorCtor = new (message: string, opts?: { retryAfter?: number; status?: number }) => PlatformError;
export const KINDS: Record<string, ErrorCtor> = { upstream_error: PlatformError, auth_error: AuthError, rate_limited: RateLimited, invalid_input: InvalidInput, not_found: NotFound, conflict: Conflict };

// wording that decides a 400/422 body (and a 200 envelope failure for the first two); the same table as errors.py
export const RATE_WORDS = /ratelimit|rate_limit|rate limit|call limit|too many|limit (?:your )?requests/;
const AUTH_WORDS = /api[ _-]?key|access[ _-]?token|unauthori[sz]ed|unauthenticated|credential|signature|not authori[sz]ed|forbidden|permission denied|invalid[ _-]token|expired[ _-]token/;
const NOT_FOUND_WORDS = /not found|does not exist|doesn't exist|not exist|no such/;
const VALIDATION_WORDS = new RegExp(
  "invalid|required|missing|must|malformed|validat|not (?:a |an )?valid|unknown (?:param|field|symbol|option|argument|value|key|currency|pair|market)|unsupported|unrecognized|\\bexpected|incorrect|wrong|" +
  "bad request|out of range|not allowed|illegal|cannot be|should be|parameter|\\bparam|field|format|parse|syntax|exceed|too (?:long|short|large|small|big)");

export interface ErrorRule { status?: number | number[]; match?: string; kind?: string }

/** The error kind for a failed answer; `rules` is the entry's `adapter.error_kinds` (first match wins). See errors.py `classify`. */
export function classify(status: number, text: string, opts: { method?: string; rules?: ErrorRule[]; envelope?: boolean } = {}): ErrorCtor {
  for (const rule of opts.rules ?? []) {
    if (!rule || typeof rule !== "object" || !(String(rule.kind) in KINDS)) continue;
    if (rule.status !== undefined && rule.status !== null && !(Array.isArray(rule.status) ? rule.status : [rule.status]).includes(status)) continue;
    if (rule.match && !(text ?? "").toLowerCase().includes(String(rule.match).toLowerCase())) continue;
    return KINDS[String(rule.kind)];
  }
  const low = (text ?? "").toLowerCase();
  const read = ["GET", "HEAD"].includes((opts.method ?? "GET").toUpperCase());
  if (opts.envelope) {
    if (RATE_WORDS.test(low)) return RateLimited;
    if (["auth", "token", "unauthorized", "not_allowed", "forbidden"].some((k) => low.includes(k))) return AuthError;
    return PlatformError;
  }
  if (status === 429) return RateLimited;
  if (status === 401 || status === 403) return RATE_WORDS.test(low) ? RateLimited : AuthError; // GitHub: 403 'API rate limit exceeded
  if (status === 404 || status === 410) return read ? NotFound : InvalidInput;
  if (status === 409) return Conflict;
  if (status === 400 || status === 422) {
    if (RATE_WORDS.test(low)) return RateLimited;
    if (AUTH_WORDS.test(low)) return AuthError;
    if (read && NOT_FOUND_WORDS.test(low)) return NotFound;
    if (status === 422 || VALIDATION_WORDS.test(low)) return InvalidInput;
  }
  return PlatformError;
}

/** The (unscrubbed) message for an HTTP failure, identical to errors.py `message_for`. */
export function messageFor(kind: ErrorCtor, status: number, text: string): string {
  let body = (text ?? "").trim();
  if (/^(?:<\?xml[^>]*>\s*)?<(?:!doctype\s+html|html[\s>])/i.test(body.slice(0, 300))) { // an HTML error page: its title, not markup
    const t = /<title[^>]*>([\s\S]*?)<\/title>/i.exec(body);
    body = "HTML page" + (t && t[1].trim() ? ": " + t[1].split(/\s+/).filter(Boolean).join(" ").slice(0, 200) : "");
  }
  body = body.slice(0, 300);
  const tail = (s: string) => s.replace(/[: ]+$/, "");
  if (kind === InvalidInput) return tail(`the platform rejected the request as invalid (${status}): ${body}`);
  if (kind === NotFound) return `not found (${status})` + (body ? `: ${body}` : "");
  if (kind === Conflict) return tail(`conflict with the platform's current state (${status}): ${body}`);
  if (kind === AuthError) return tail(`platform refused the credentials (${status}): ${body.slice(0, 200)}`);
  return tail(`platform error ${status}: ${body}`);
}
