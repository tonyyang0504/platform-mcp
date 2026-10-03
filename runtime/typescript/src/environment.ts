/** Vendor environments (sandbox, test) for one served entry: the same rules as the Python runtime's
 *  environment.py (read that module's docstring for the catalog block). PLATFORM_MCP_<ID>_ENV selects a
 *  declared environment (unset, empty or "production" = production); PLATFORM_MCP_<ID>_BASE_URL points
 *  the server at any https host. A bad value is an invalid_input tool error naming the variable; the
 *  override value is never echoed and is redacted from every later message. */
import { envName, registerSecret } from "./credentials.js";
import { InvalidInput } from "./errors.js";

export const PRODUCTION = "production";
const NAME_RE = /^[a-z][a-z0-9_]{0,31}$/;
const HTTPS_URL_RE = /^https:\/\/(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*|\[[0-9A-Fa-f:.]+\])(?::[0-9]{1,5})?(?:\/[^\s?#]*)?$/;

export interface EnvironmentSpec {
  base_url?: string; token_url?: string; auth_url?: string; scope?: string; login_path?: string;
  hosts?: Record<string, string>; headers?: Record<string, string>; same_host?: boolean;
  docs?: string; verified_at?: string; notes?: string;
}

export function validHttpsUrl(value: string): boolean { return HTTPS_URL_RE.test(value ?? ""); }

function hostOf(url: string): string {
  const m = /^[a-z][a-z0-9+.-]*:\/\/([^/?#]*)/i.exec(url ?? "");
  return m ? m[1] : "";
}

function rehost(url: unknown, hosts: Record<string, string>): unknown {
  if (typeof url !== "string" || !url.startsWith("https://") || !hosts || !Object.keys(hosts).length) return url;
  const host = hostOf(url);
  return Object.prototype.hasOwnProperty.call(hosts, host) ? "https://" + hosts[host] + url.slice("https://".length + host.length) : url;
}

function whyInvalid(value: string): string {
  const v = value.trim();
  if (!v.toLowerCase().startsWith("https://")) return "it must start with https://";
  const rest = v.slice("https://".length);
  if (rest.split("/", 1)[0].includes("@")) return "it must not carry user info (credentials) before the host";
  if (rest.includes("?") || rest.includes("#")) return "it must not carry a query string or fragment";
  return "it must be https://host[:port][/path] with a valid host name";
}

/** The effective adapter for this process (a copy) and the environment name (`production`, a declared
 *  environment, suffixed `+base_url` when the operator override is in effect). */
export function selectEnvironment(platformId: string, adapter: any, env: Record<string, string | undefined> = process.env): { adapter: any; environment: string } {
  const variable = envName(platformId, "ENV");
  let name = (env[variable] ?? "").trim().toLowerCase() || PRODUCTION;
  const declared: Record<string, EnvironmentSpec> = adapter.environments ?? {};
  const { environments: _drop, ...rest } = adapter;
  const out: any = structuredClone(rest);
  const available = () => [PRODUCTION, ...Object.keys(declared).sort()].join(", ");
  if (name !== PRODUCTION) {
    if (!NAME_RE.test(name)) throw new InvalidInput(`configuration: ${variable} must be an environment name (${available()})`);
    if (!Object.prototype.hasOwnProperty.call(declared, name)) throw new InvalidInput(`configuration: ${variable}=${name} is not an environment of this server; available: ${available()}`);
    const spec = declared[name];
    const auth = (out.auth ??= { type: "none" });
    const hosts = spec.hosts ?? {};
    if (Object.keys(hosts).length) {
      for (const tool of Object.values<any>(out.tools ?? {})) if (typeof tool.path === "string") tool.path = rehost(tool.path, hosts);
      if (auth.login && typeof auth.login.path === "string") auth.login.path = rehost(auth.login.path, hosts);
      if (auth.token_url) auth.token_url = rehost(auth.token_url, hosts);
      out.base_url = rehost(out.base_url, hosts);
    }
    if (spec.base_url) out.base_url = spec.base_url;
    if (spec.token_url) auth.token_url = spec.token_url;
    if (spec.scope) auth.scope = spec.scope;
    if (spec.login_path && auth.login && typeof auth.login === "object") auth.login.path = spec.login_path;
    if (spec.auth_url) auth.auth_url = spec.auth_url;
    if (spec.headers) out.headers = { ...(out.headers ?? {}), ...spec.headers };
  }
  const overrideVar = envName(platformId, "BASE_URL");
  const override = (env[overrideVar] ?? "").trim();
  if (override) {
    if (override.replace(/^[A-Za-z][A-Za-z0-9+.-]*:\/\//, "").length >= 6) registerSecret(override); // an operator's private gateway never appears in a message (a bare scheme is not a secret)
    if (!validHttpsUrl(override)) throw new InvalidInput(`configuration: ${overrideVar} is not a valid override: ${whyInvalid(override)}`);
    out.base_url = override;
    name = `${name}+base_url`;
  }
  return { adapter: out, environment: name };
}

/** Rotated refresh tokens are saved per environment: a sandbox token must never replace a production one. */
export function stateKey(platformId: string, environment: string): string {
  const base = environment.split("+", 1)[0];
  return base === PRODUCTION ? platformId : `${platformId}.${base}`;
}
