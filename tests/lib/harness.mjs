// Shared harness for TypeScript contract tests: a catalog entry served over an in-memory MCP link with a
// mocked fetch. `handler(url, init, n)` returns {status?, body?, type?, headers?}; every request is logged.
import { readFileSync } from "node:fs";
import { Client, InMemoryTransport } from "../../runtime/typescript/node_modules/@modelcontextprotocol/client/dist/index.mjs";
import { buildServer, Transport } from "../../runtime/typescript/dist/index.js";

export const loadSpec = (category, id) => JSON.parse(readFileSync(new URL(`../../catalog/${category}/${id}.json`, import.meta.url), "utf8"));

export function response(status, body, type = "application/json", headers = {}, bytes = undefined) {
  const lower = Object.fromEntries(Object.entries(headers).map(([k, v]) => [k.toLowerCase(), v]));
  if (type && (body !== undefined || bytes)) lower["content-type"] = type;
  return {
    status,
    headers: { get: (k) => lower[k.toLowerCase()] ?? null, forEach: (fn) => Object.entries(lower).forEach(([k, v]) => fn(v, k)) },
    text: async () => (bytes ? Buffer.from(bytes).toString("utf8") : body === undefined ? "" : typeof body === "string" ? body : JSON.stringify(body)),
    ...(bytes ? { arrayBuffer: async () => Uint8Array.from(bytes).buffer } : {}),
  };
}

export async function connect(spec, handler, creds = {}) {
  const log = [];
  const fetcher = async (url, init) => {
    log.push({ url: new URL(url), init });
    const r = handler(new URL(url), init, log.length);
    return response(r.status ?? 200, r.body, r.type, r.headers, r.bytes);
  };
  const a = spec.adapter;
  const transport = new Transport(a.base_url, a.auth, { ...creds }, 50, "test", fetcher, a.envelope ?? {});
  const server = buildServer(spec, transport);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(ct);
  const call = async (name, args) => client.callTool({ name, arguments: args });
  return { client, log, call };
}
