import { McpServer } from "@modelcontextprotocol/server";
import { StdioServerTransport } from "@modelcontextprotocol/server/stdio";
import { Adapter, type Spec } from "./adapter.js";
import { resolve, scrub } from "./credentials.js";
import { selectEnvironment, stateKey } from "./environment.js";
import { PlatformError } from "./errors.js";
import { Transport, type Fetcher } from "./http.js";
import { vocabFor } from "./vocab.js";
import { clean } from "./sanitize.js";

/** A JSON-Schema-carrying "standard schema" so the SDK advertises exactly the vocabulary's schemas. */
function jsonSchema(schema: Record<string, unknown>) {
  return {
    "~standard": {
      version: 1 as const, vendor: "platform-mcp",
      validate: (value: unknown) => ({ value }),
      jsonSchema: { input: () => schema, output: () => schema },
    },
  };
}

function result(payload: Record<string, unknown>, isError = false) {
  return { content: [{ type: "text" as const, text: JSON.stringify(payload) }], structuredContent: payload, isError };
}

/** One adapter (and so one transport: minted tokens, rotated refresh tokens, the rate limit and the response cache)
 *  shared by every McpServer a factory builds. Streamable HTTP builds a server per request; without this each
 *  request would log in again and a single-use rotated refresh token would be lost after the first call. */
export interface SharedState { adapter?: Adapter }

export function buildServer(spec: Spec, transport?: Transport, fetcher?: Fetcher, shared: SharedState = {}): McpServer {
  const vocab = vocabFor(spec as any);
  const a = spec.adapter;
  // catalog text is cleaned before a client's model reads it (sanitize.ts): an entry may come from a hostile document
  const label = clean(spec.label ?? spec.id, "label");
  const generic = spec.category === "generic";
  const server = new McpServer({ name: `${spec.id}-mcp`, title: generic ? label : `${label} (${spec.category})`, version: spec.version ?? "0.1.0" }, {
    instructions: clean(spec.instructions, "instructions") || (generic
      ? `Tools for the ${label} API. Every tool maps to an endpoint documented at ${clean(spec.docs_url, "instructions")}. Results are the API's own answer under \`data\`; read tools take \`select_fields\` to return only some fields.`
      : `Tools for ${label}, a ${spec.category.replace(/_/g, " ")} platform. Every tool maps to an endpoint documented on the platform's developer pages (${clean(spec.docs_url, "instructions")}). Results carry a normalised shape plus the raw record under \`raw\`.`),
  });
  const getAdapter = () => {
    if (!shared.adapter) {
      // PLATFORM_MCP_<ID>_ENV / _BASE_URL (environment.ts): an injected transport keeps its own base URL
      const { adapter: eff, environment } = selectEnvironment(spec.id, a);
      const creds = transport ? {} : resolve(spec.id, eff.auth ?? { fields: [] }, eff.config_fields ?? []);
      let ua = `platform-mcp/${spec.id} (+https://github.com/tonyyang0504/platform-mcp)`;
      if (eff.user_agent_field && creds[eff.user_agent_field]) ua = `${ua} ${creds[eff.user_agent_field]}`;
      const t = transport ?? new Transport(eff.base_url, { ...(eff.auth ?? { type: "none" }), state_key: stateKey(spec.id, environment) } as any, creds, eff.rate_per_second ?? 2, ua, fetcher, eff.envelope ?? {});
      t.fixedHeaders = { ...t.fixedHeaders, ...(eff.headers ?? {}) };
      if (eff.error_kinds) t.errorKinds = eff.error_kinds;
      shared.adapter = new Adapter({ ...spec, adapter: eff }, t, transport ? t.creds : creds);
    }
    return shared.adapter;
  };
  for (const [verb, ts] of Object.entries(a.tools)) {
    const v = vocab[verb];
    if (!v) throw new Error(`unknown verb ${verb} for category ${spec.category}`);
    server.registerTool(verb, {
      title: v.title,
      description: v.description + (ts.note ? ` ${clean(ts.note, "note")}` : ""),
      inputSchema: jsonSchema(v.input) as any,
      outputSchema: jsonSchema(v.output) as any,
      annotations: { title: v.title, readOnlyHint: v.read_only, destructiveHint: v.destructive ?? !v.read_only, idempotentHint: v.idempotent ?? v.read_only, openWorldHint: true },
      // null (not absent) when the entry has no value, exactly as the Python runtime sends it
      _meta: { "platform_mcp/endpoint": ts.path ?? null, "platform_mcp/docs": ts.docs || spec.docs_url || null, "platform_mcp/verified_at": spec.verified_at ?? null },
    }, async (args: any) => {
      try { return result(await getAdapter().call(verb, args ?? {})); }
      catch (e) {
        if (e instanceof PlatformError) return result(e.payload(), true);
        return result({ error: "internal_error", message: scrub(`${(e as Error).name}: ${(e as Error).message}`).slice(0, 300) }, true);
      }
    });
  }
  return server;
}

/** A factory for Streamable HTTP: every server it builds shares one adapter/transport (see SharedState). */
export function serverFactory(spec: Spec, fetcher?: Fetcher): () => McpServer {
  const shared: SharedState = {};
  return () => buildServer(spec, undefined, fetcher, shared);
}

export async function runStdio(spec: Spec): Promise<void> {
  const server = buildServer(spec);
  await server.connect(new StdioServerTransport());
}

/** CLI entry shared by generated packages: stdio by default, `--http [--host H] [--port N]` for Streamable HTTP. */
export async function main(spec: Spec, argv: string[] = process.argv.slice(2)): Promise<void> {
  const flag = (name: string) => { const i = argv.indexOf(name); return i >= 0 ? argv[i + 1] : undefined; };
  if (argv.includes("--http")) {
    const { serveHttp, httpAuthToken } = await import("./http_server.js");
    const host = flag("--host") ?? "127.0.0.1";
    let token: string | undefined;
    try { token = httpAuthToken(host, argv.includes("--allow-remote")); }
    catch (e) { console.error(`platform-mcp: ${(e as Error).message}`); process.exit(2); }
    await serveHttp(serverFactory(spec), host, Number(flag("--port") ?? 8000), "/mcp", token);
  } else await runStdio(spec);
}
