/** Outbound URL guard for URLs that do not come from the catalog (multipart `file:<arg>` downloads): the
 *  same table as the Python runtime's netguard.py. Every address the host resolves to must be public;
 *  loopback, private, link-local (cloud metadata), CGNAT, multicast, reserved and documentation ranges and
 *  their IPv6 forms (mapped, NAT64, 6to4) are refused, and a host that does not resolve is refused too.
 *  PLATFORM_MCP_ALLOW_PRIVATE_URLS=1 turns the guard off. The caller connects to the vetted address itself
 *  (`pinnedGet`: node:http(s) with a fixed lookup, the original Host header and TLS server name), so a DNS answer
 *  that changes after the check (rebinding) is never used. tests/fixtures/netguard_cases.json is checked against both runtimes. */
import dns from "node:dns";
import http from "node:http";
import https from "node:https";
import net from "node:net";
import { InvalidInput } from "./errors.js";

export const ALLOW_ENV = "PLATFORM_MCP_ALLOW_PRIVATE_URLS";
export type Resolver = (host: string) => Promise<string[]>;

const V4: [string, number][] = [["0.0.0.0", 8], ["10.0.0.0", 8], ["100.64.0.0", 10], ["127.0.0.0", 8], ["169.254.0.0", 16], ["172.16.0.0", 12], ["192.0.0.0", 24],
  ["192.0.2.0", 24], ["192.88.99.0", 24], ["192.168.0.0", 16], ["198.18.0.0", 15], ["198.51.100.0", 24], ["203.0.113.0", 24], ["224.0.0.0", 4], ["240.0.0.0", 4]];
const V6: [string, number][] = [["::", 96], ["100::", 64], ["2001:db8::", 32], ["fc00::", 7], ["fe80::", 10], ["fec0::", 10], ["ff00::", 8]];

function v4ToBig(ip: string): bigint {
  return ip.split(".").reduce((acc, part) => (acc << 8n) | BigInt(Number(part)), 0n);
}
function v6ToBig(ip: string): bigint {
  let text = ip;
  const tail = /(\d+\.\d+\.\d+\.\d+)$/.exec(text); // an embedded IPv4 tail (::ffff:1.2.3.4)
  if (tail) { const v = v4ToBig(tail[1]); text = text.slice(0, -tail[1].length) + ((v >> 16n) & 0xffffn).toString(16) + ":" + (v & 0xffffn).toString(16); }
  const [head, rest] = text.includes("::") ? text.split("::") : [text, undefined];
  const h = head ? head.split(":") : []; const r = rest !== undefined && rest !== "" ? rest.split(":") : [];
  const groups = rest === undefined ? h : [...h, ...Array(8 - h.length - r.length).fill("0"), ...r];
  return groups.reduce((acc, g) => (acc << 16n) | BigInt(parseInt(g || "0", 16)), 0n);
}
const inRange = (v: bigint, base: bigint, bits: number, width: number) => (v >> BigInt(width - bits)) === (base >> BigInt(width - bits));

/** True only for a literal IPv4/IPv6 address outside every blocked range. */
export function isPublicIp(text: string): boolean {
  const ip = String(text).split("%")[0].replace(/^\[|\]$/g, "");
  const kind = net.isIP(ip);
  if (kind === 4) { const v = v4ToBig(ip); return !V4.some(([b, n]) => inRange(v, v4ToBig(b), n, 32)); }
  if (kind !== 6) return false;
  const v = v6ToBig(ip.toLowerCase());
  const v4of = (x: bigint) => [Number((x >> 24n) & 255n), Number((x >> 16n) & 255n), Number((x >> 8n) & 255n), Number(x & 255n)].join(".");
  if ((v >> 32n) === 0xffffn) return isPublicIp(v4of(v & 0xffffffffn)); // ::ffff:a.b.c.d
  if (inRange(v, v6ToBig("64:ff9b::"), 96, 128)) return isPublicIp(v4of(v & 0xffffffffn)); // NAT64
  if (inRange(v, v6ToBig("2002::"), 16, 128)) return isPublicIp(v4of((v >> 80n) & 0xffffffffn)); // 6to4
  return !V6.some(([b, n]) => inRange(v, v6ToBig(b), n, 128));
}

export const defaultResolver: Resolver = async (host) => [...new Set((await dns.promises.lookup(host, { all: true, verbatim: true })).map((a) => a.address))].sort();

/** Throw InvalidInput unless `url` is http(s) and every address its host resolves to is public. Returns the vetted
 *  addresses to connect to, or undefined when the operator turned the guard off. */
export async function checkUrl(url: string, resolver: Resolver = defaultResolver, what = "URL"): Promise<string[] | undefined> {
  if (process.env[ALLOW_ENV] === "1") return undefined;
  let u: URL;
  try { u = new URL(String(url)); } catch { throw new InvalidInput(`${what} must be an http(s) URL with a host`); }
  const host = u.hostname.replace(/^\[|\]$/g, "").toLowerCase();
  if (!["http:", "https:"].includes(u.protocol) || !host) throw new InvalidInput(`${what} must be an http(s) URL with a host`);
  if (host === "localhost" || host.endsWith(".localhost")) throw new InvalidInput(`${what} points at this machine (localhost); set ${ALLOW_ENV}=1 to allow private addresses`);
  let addresses: string[];
  if (net.isIP(host.split("%")[0])) addresses = [host];
  else {
    try { addresses = await resolver(host); } catch { addresses = []; }
    if (!addresses.length) throw new InvalidInput(`${what}: the host does not resolve`);
  }
  if (!addresses.every(isPublicIp)) throw new InvalidInput(`${what} resolves to a private, loopback, link-local or reserved address; set ${ALLOW_ENV}=1 to allow it`);
  return addresses.map((a) => a.split("%")[0]);
}

/** The address to connect to: the first IPv4 one, else the first (netguard.py pick). */
export function pick(addresses: string[]): string { return addresses.find((a) => net.isIP(a) === 4) ?? addresses[0]; }

export interface PinnedResponse { status: number; headers: { get(k: string): string | null }; body: AsyncIterable<Uint8Array>; destroy(): void }
/** GET `url` over a connection to `address` (no DNS lookup of the host): Host header and TLS server name (and so the
 *  certificate check) stay the URL's host. */
export function pinnedGet(url: string, address: string, headers: Record<string, string> = {}, timeoutMs = 30000): Promise<PinnedResponse> {
  const u = new URL(url);
  const host = u.hostname.replace(/^\[|\]$/g, "");
  const family = net.isIP(address);
  const mod = u.protocol === "https:" ? https : http;
  return new Promise((resolve, reject) => {
    const req = mod.request({
      protocol: u.protocol, hostname: host, port: u.port || undefined, path: u.pathname + u.search, method: "GET", headers, agent: false,
      ...(u.protocol === "https:" && !net.isIP(host) ? { servername: host } : {}),
      lookup: ((_h: string, opts: any, cb: any) => (opts && opts.all ? cb(null, [{ address, family }]) : cb(null, address, family))) as any,
    }, (res) => resolve({
      status: res.statusCode ?? 0,
      headers: { get: (k: string) => { const v = res.headers[k.toLowerCase()]; return v === undefined ? null : Array.isArray(v) ? v.join(", ") : String(v); } },
      body: res, destroy: () => res.destroy(),
    }));
    req.on("error", reject);
    req.setTimeout(timeoutMs, () => req.destroy(new Error("timeout")));
    req.end();
  });
}
