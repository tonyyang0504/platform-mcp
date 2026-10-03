import crypto from "node:crypto";
import { createServer, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import { NodeStreamableHTTPServerTransport, localhostHostValidation } from "@modelcontextprotocol/node";
import type { McpServer } from "@modelcontextprotocol/server";

export const LOOPBACK_HOSTS = ["127.0.0.1", "localhost", "::1"];
export const TOKEN_ENV = "PLATFORM_MCP_HTTP_TOKEN";
const MIN_TOKEN = 24;

/** The bearer token every HTTP request must carry, or undefined (loopback without a token). A server acts with the
 *  operator's credentials, so a non-loopback bind needs BOTH --allow-remote and PLATFORM_MCP_HTTP_TOKEN; otherwise an
 *  Error (never repeating the token). Same rules as the Python runtime's http_auth_token. */
export function httpAuthToken(host: string, allowRemote: boolean, env: Record<string, string | undefined> = process.env): string | undefined {
  const token = (env[TOKEN_ENV] ?? "").trim() || undefined;
  if (token !== undefined && token.length < MIN_TOKEN) throw new Error(`${TOKEN_ENV} must be at least ${MIN_TOKEN} characters (a random secret)`);
  if (!LOOPBACK_HOSTS.includes(host) && !(allowRemote && token)) {
    throw new Error(`refusing to serve HTTP on '${host}': the server acts with the operator's credentials. Bind 127.0.0.1, or pass --allow-remote AND set ${TOKEN_ENV} (clients send 'Authorization: Bearer <token>')`);
  }
  return token;
}

function bearerOk(header: string | undefined, token: string): boolean {
  if (!header || header.slice(0, 7).toLowerCase() !== "bearer ") return false;
  const got = Buffer.from(header.slice(7).trim()); const want = Buffer.from(token);
  return got.length === want.length && crypto.timingSafeEqual(got, want);
}

/** Streamable HTTP (stateless) on a single /mcp endpoint using node:http; with `token`, every request needs
 *  `Authorization: Bearer <token>`. Resolves with the listening server (port 0 picks a free port). */
export async function serveHttp(build: () => McpServer, host = "127.0.0.1", port = 8000, path = "/mcp", token?: string): Promise<Server> {
  const guard = LOOPBACK_HOSTS.includes(host) ? localhostHostValidation() : undefined;
  const server = createServer(async (req, res) => {
    if (token && !bearerOk(req.headers.authorization, token)) {
      res.statusCode = 401; res.setHeader("WWW-Authenticate", 'Bearer realm="platform-mcp"'); res.setHeader("Content-Type", "application/json");
      res.end('{"error": "unauthorized"}'); return;
    }
    if (guard && !guard(req, res)) return;
    const url = new URL(req.url ?? "/", `http://${req.headers.host ?? host}`);
    if (url.pathname !== path) { res.statusCode = 404; res.end(); return; }
    if (req.method !== "POST") { res.statusCode = 405; res.setHeader("Allow", "POST"); res.end(); return; }
    const mcp = build();
    const transport = new NodeStreamableHTTPServerTransport({ sessionIdGenerator: undefined });
    res.on("close", () => { void transport.close(); void mcp.close(); });
    await mcp.connect(transport);
    await transport.handleRequest(req, res);
  });
  await new Promise<void>((resolve) => server.listen(port, host, resolve));
  console.error(`platform-mcp: Streamable HTTP on http://${host}:${(server.address() as AddressInfo).port}${path}${token ? " (bearer token required)" : ""}`);
  return server;
}
