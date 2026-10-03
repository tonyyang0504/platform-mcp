"""Catalog text shown to MCP clients (server instructions, tool notes appended to descriptions, labels in titles).
A catalog entry may have been written from a hostile API document, and a client's model reads these strings as
trusted tool documentation, so they are cleaned before exposure: invisible and bidirectional-control characters
are removed, control characters and line separators become spaces, whitespace is collapsed, well-known prompt
injection markers are replaced with "[removed]", and the text is capped. The lint refuses the same problems in
the catalog itself. The TypeScript runtime's sanitize.ts is identical (tests/fixtures/sanitize_cases.json)."""
import re
import unicodedata

CAPS = {"label": 120, "note": 1500, "instructions": 2000}
_INVISIBLE = re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff]")
MARKERS = re.compile(
    r"ignore\s+(?:all\s+|any\s+)?(?:the\s+)?(?:previous|prior|above|earlier|preceding)\s+(?:instructions|prompts?|rules|messages)"
    r"|disregard\s+(?:all\s+|any\s+)?(?:the\s+)?(?:previous|prior|above|earlier|preceding)\s+[a-z]+"
    r"|</?\s*(?:system|assistant|user|developer|instructions?|tool_call|function_call)\s*>"
    r"|<\|[^|<>]{1,40}\|>"
    r"|\[/?INST\]"
    r"|<<\s*/?SYS\s*>>"
    r"|(?:BEGIN|END)\s+(?:SYSTEM|DEVELOPER)\s+(?:PROMPT|MESSAGE|INSTRUCTIONS)"
    r"|you\s+are\s+now\s+(?:a|an|the|in)\b"
    r"|new\s+(?:system\s+)?instructions\s*:",
    re.I,
)


def _spaces(text: str) -> str:
    text = _INVISIBLE.sub("", text)
    text = "".join(" " if unicodedata.category(c) == "Cc" or c in "\u2028\u2029" else c for c in text)
    return re.sub(r"[ \t\u00a0\u1680\u2000-\u200a\u202f\u205f\u3000]+", " ", text).strip()


def clean(text, kind: str = "note") -> str:
    """The string a client may see."""
    if text is None:
        return ""
    out = MARKERS.sub("[removed]", _spaces(str(text)))
    cap = CAPS[kind]
    return out if len(out) <= cap else out[: cap - 1].rstrip() + "…"


def problems(text, kind: str = "note") -> list[str]:
    """Why catalog text would be altered before exposure (the lint reports these as errors)."""
    if text is None:
        return []
    if not isinstance(text, str):
        return ["must be a string"]
    out = []
    if _INVISIBLE.search(text) or any(unicodedata.category(c) == "Cc" and c not in "\n\t" or c in "\u2028\u2029" for c in text):
        out.append("contains control or invisible characters")
    if MARKERS.search(_spaces(text)):
        out.append("contains a prompt-injection marker (e.g. 'ignore previous instructions', '<system>')")
    if len(_spaces(text)) > CAPS[kind]:
        out.append(f"is longer than {CAPS[kind]} characters")
    return out
