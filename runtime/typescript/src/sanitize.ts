/** Catalog text shown to MCP clients (server instructions, tool notes, labels): the same cleaning as the Python
 *  runtime's sanitize.py — invisible/bidi characters removed, control characters and line separators to spaces,
 *  whitespace collapsed, prompt-injection markers replaced with "[removed]", length capped (code points). */
export const CAPS: Record<string, number> = { label: 120, note: 1500, instructions: 2000 };
const INVISIBLE = /[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff]/g;
const MARKERS = new RegExp(
  "ignore\\s+(?:all\\s+|any\\s+)?(?:the\\s+)?(?:previous|prior|above|earlier|preceding)\\s+(?:instructions|prompts?|rules|messages)"
  + "|disregard\\s+(?:all\\s+|any\\s+)?(?:the\\s+)?(?:previous|prior|above|earlier|preceding)\\s+[a-z]+"
  + "|</?\\s*(?:system|assistant|user|developer|instructions?|tool_call|function_call)\\s*>"
  + "|<\\|[^|<>]{1,40}\\|>"
  + "|\\[/?INST\\]"
  + "|<<\\s*/?SYS\\s*>>"
  + "|(?:BEGIN|END)\\s+(?:SYSTEM|DEVELOPER)\\s+(?:PROMPT|MESSAGE|INSTRUCTIONS)"
  + "|you\\s+are\\s+now\\s+(?:a|an|the|in)\\b"
  + "|new\\s+(?:system\\s+)?instructions\\s*:", "gi");

function spaces(text: string): string {
  return text.replace(INVISIBLE, "").replace(/[\u0000-\u001f\u007f-\u009f\u2028\u2029]/g, " ")
    .replace(/[ \t\u00a0\u1680\u2000-\u200a\u202f\u205f\u3000]+/g, " ").trim();
}

/** The string a client may see. */
export function clean(text: unknown, kind = "note"): string {
  if (text === undefined || text === null) return "";
  const out = Array.from(spaces(String(text)).replace(MARKERS, "[removed]"));
  const cap = CAPS[kind];
  return out.length <= cap ? out.join("") : out.slice(0, cap - 1).join("").trimEnd() + "…";
}
