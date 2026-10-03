/** Generic entries: tools defined by the API itself, not by a category vocabulary. The same rules as the Python
 *  runtime's generic.py (tests/fixtures/generic_cases.json runs the same cases in both): each tool carries its own
 *  title, description and input schema; the answer is passed through as {data}, narrowed by result.root, the selected
 *  fields (result.select or the per-call `select_fields` argument) and result.max_items. */
import { clean } from "./sanitize.js";

export const CATEGORY = "generic";
export const SELECT_ARG = "select_fields";
export const DEFAULT_MAX_ITEMS = 100;
export const TOOL_NAME_RE = /^[a-z][a-z0-9_]{0,63}$/;
export const OUTPUT_SCHEMA = {
  type: "object",
  properties: {
    data: { description: "The API's answer (narrowed by result.root and the selected fields)." },
    truncated: { type: "boolean", description: "The list in `data` was cut to max_items records." },
    total_items: { type: "integer", description: "How many records the list had before it was cut." },
  },
  required: ["data"],
};
const SELECT_SCHEMA = { type: "array", items: { type: "string" }, description: "Optional: return only these fields of each record (dotted paths such as id or owner.login)." };

export const isGeneric = (spec: { category?: string }) => spec.category === CATEGORY;

export function annotations(tool: Record<string, any>): { read_only: boolean; destructive: boolean; idempotent: boolean } {
  const m = String(tool.method ?? "GET").toUpperCase();
  const read_only = Boolean(tool.read_only ?? (m === "GET" || m === "HEAD"));
  const destructive = Boolean(tool.destructive ?? (!read_only && m === "DELETE"));
  const idempotent = Boolean(tool.idempotent ?? (read_only || m === "PUT" || m === "DELETE"));
  return { read_only, destructive, idempotent };
}

function cleanSchema(node: unknown): unknown {
  if (Array.isArray(node)) return node.map(cleanSchema);
  if (node && typeof node === "object") {
    return Object.fromEntries(Object.entries(node as Record<string, unknown>).map(([k, v]) => [k, (k === "description" || k === "title") && typeof v === "string" ? clean(v, "note") : cleanSchema(v)]));
  }
  return node;
}

export function inputSchema(tool: Record<string, any>): Record<string, any> {
  let schema = cleanSchema(JSON.parse(JSON.stringify(tool.input ?? {}))) as Record<string, any>;
  if (!schema || typeof schema !== "object" || Array.isArray(schema)) schema = {};
  // the same key order as Python (type, properties, ..., additionalProperties), so the advertised schemas are identical
  const out: Record<string, any> = { ...schema, type: "object" };
  if (!("properties" in out)) out.properties = {};
  if (!("additionalProperties" in out)) out.additionalProperties = false;
  if (annotations(tool).read_only && !(SELECT_ARG in out.properties)) out.properties[SELECT_ARG] = JSON.parse(JSON.stringify(SELECT_SCHEMA));
  return out;
}

export function titleOf(name: string, tool: Record<string, any>): string {
  const t = tool.title || (name.replace(/_/g, " ").trim().charAt(0).toUpperCase() + name.replace(/_/g, " ").trim().slice(1).toLowerCase());
  return clean(t, "label");
}

export function vocab(spec: { adapter?: { tools?: Record<string, any> } }): Record<string, any> {
  const out: Record<string, any> = {};
  for (const [name, tool] of Object.entries(spec.adapter?.tools ?? {})) {
    out[name] = { title: titleOf(name, tool), description: clean(tool.description || titleOf(name, tool), "note"), ...annotations(tool),
                  input: inputSchema(tool), output: JSON.parse(JSON.stringify(OUTPUT_SCHEMA)) };
  }
  return out;
}

function dig(obj: unknown, path: string): unknown {
  if (!path || path === "$") return obj;
  let cur: any = obj;
  for (const part of path.split(".")) {
    if (part === "*") {
      if (cur && typeof cur === "object" && !Array.isArray(cur)) { const vals = Object.values(cur); cur = vals.length ? vals[0] : undefined; }
      else if (Array.isArray(cur)) cur = cur.length ? cur[0] : undefined;
      else return undefined;
    } else if (cur && typeof cur === "object" && !Array.isArray(cur)) cur = cur[part];
    else if (Array.isArray(cur) && /^\d+$/.test(part)) cur = cur[Number(part)];
    else return undefined;
  }
  return cur;
}

function project(record: unknown, select: string[]): unknown {
  if (!record || typeof record !== "object" || Array.isArray(record)) return record;
  return Object.fromEntries(select.map((p) => [p, dig(record, p) ?? null]));
}

export function shape(data: unknown, tool: Record<string, any>, args: Record<string, unknown>): Record<string, unknown> {
  const result = tool.result ?? {};
  if (data && typeof data === "object" && (data as any).__unparsed__ !== undefined) data = (data as any).text; // a plain-text answer is still the answer
  if (result.root) data = dig(data, result.root);
  let select: unknown = args[SELECT_ARG] || result.select;
  if (typeof select === "string") select = select.split(",").map((s) => s.trim()).filter(Boolean);
  if (Array.isArray(select) && select.length) {
    const sel = select.map(String);
    data = Array.isArray(data) ? data.map((r) => project(r, sel)) : project(data, sel);
  }
  if (data === undefined) data = null;
  const limit = Number(result.max_items || DEFAULT_MAX_ITEMS);
  if (Array.isArray(data) && data.length > limit) return { data: data.slice(0, limit), truncated: true, total_items: data.length };
  return { data };
}
