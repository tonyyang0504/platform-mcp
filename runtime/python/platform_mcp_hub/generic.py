"""Generic entries: tools defined by the API itself, not by a category vocabulary.

An entry with ``"category": "generic"`` describes each tool in its own adapter block, straight from the API's
operations: ``title``, ``description``, ``input`` (a JSON Schema object for the arguments), the HTTP mapping
(``method``, ``path``, ``params``, ``body`` with the same expressions as every other entry) and ``docs`` (the
documented endpoint). The result is the API's own answer, passed through as ``{"data": ...}``, optionally narrowed:

  result.root       dotted path to the part of the answer to return (``items``, ``data.results``)
  result.select     default fields to keep from each record (dotted paths: ``id``, ``owner.login``)
  result.max_items  a list longer than this is cut (default 100) and ``truncated: true`` says so

and every read tool accepts ``select_fields`` (a list of dotted paths) to choose fields per call. Annotations come
from the method unless the tool sets ``read_only`` / ``destructive`` / ``idempotent`` (a POST search is a read).
Text that reaches an MCP client (descriptions, titles, schema descriptions) is sanitised like all catalog text.
The TypeScript runtime's generic.ts implements the same rules (tests/fixtures/generic_cases.json)."""

from __future__ import annotations

import copy
import re
from typing import Any

from .sanitize import clean

CATEGORY = "generic"
SELECT_ARG = "select_fields"
DEFAULT_MAX_ITEMS = 100
TOOL_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
RESULT_KEYS = {"root", "select", "max_items"}
TOOL_KEYS = {"title", "description", "input", "method", "path", "params", "path_params", "fixed_params", "body", "body_format",
             "xml_root", "headers", "query_safe", "sign", "csv", "cache_ttl", "result", "docs", "note", "read_only", "destructive",
             "idempotent"}
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "data": {"description": "The API's answer (narrowed by result.root and the selected fields)."},
        "truncated": {"type": "boolean", "description": "The list in `data` was cut to max_items records."},
        "total_items": {"type": "integer", "description": "How many records the list had before it was cut."},
    },
    "required": ["data"],
}
SELECT_SCHEMA = {"type": "array", "items": {"type": "string"},
                 "description": "Optional: return only these fields of each record (dotted paths such as id or owner.login)."}


def is_generic(spec: dict) -> bool:
    return spec.get("category") == CATEGORY


def _method(tool: dict) -> str:
    return str(tool.get("method", "GET")).upper()


def annotations(tool: dict) -> dict:
    m = _method(tool)
    read_only = bool(tool.get("read_only", m in ("GET", "HEAD")))
    destructive = bool(tool.get("destructive", (not read_only) and m == "DELETE"))
    idempotent = bool(tool.get("idempotent", read_only or m in ("PUT", "DELETE")))
    return {"read_only": read_only, "destructive": destructive, "idempotent": idempotent}


def _clean_schema(node: Any) -> Any:
    """A copy of a JSON Schema with every `description` and `title` sanitised (they reach the client's model)."""
    if isinstance(node, dict):
        return {k: (clean(v, "note") if k in ("description", "title") and isinstance(v, str) else _clean_schema(v)) for k, v in node.items()}
    if isinstance(node, list):
        return [_clean_schema(v) for v in node]
    return node


def input_schema(tool: dict) -> dict:
    schema = _clean_schema(copy.deepcopy(tool.get("input") or {}))
    if not isinstance(schema, dict):
        schema = {}
    schema["type"] = "object"
    schema.setdefault("properties", {})
    schema.setdefault("additionalProperties", False)
    if annotations(tool)["read_only"] and SELECT_ARG not in schema["properties"]:
        schema["properties"][SELECT_ARG] = copy.deepcopy(SELECT_SCHEMA)
    return schema


def title_of(name: str, tool: dict) -> str:
    return clean(tool.get("title") or name.replace("_", " ").strip().capitalize(), "label")


def vocab(spec: dict) -> dict:
    """The per-tool definitions a vocabulary would give, built from the entry itself."""
    out = {}
    for name, tool in (spec.get("adapter") or {}).get("tools", {}).items():
        a = annotations(tool)
        out[name] = {"title": title_of(name, tool), "description": clean(tool.get("description") or title_of(name, tool), "note"),
                     **a, "input": input_schema(tool), "output": copy.deepcopy(OUTPUT_SCHEMA)}
    return out


def _dig(obj: Any, path: str | None) -> Any:
    from .adapter import _dig as dig
    return dig(obj, path)


def _project(record: Any, select: list[str]) -> Any:
    if not isinstance(record, dict):
        return record
    return {p: _dig(record, p) for p in select}


def shape(data: Any, tool: dict, args: dict) -> dict:
    """{"data": the answer (after result.root, the selected fields and max_items)} [+ truncated, total_items]."""
    result = tool.get("result") or {}
    if isinstance(data, dict) and hasattr(data, "ctype"):  # UnparsedText: a plain-text answer is still the answer
        data = data.get("text")
    if result.get("root"):
        data = _dig(data, result["root"])
    select = args.get(SELECT_ARG) or result.get("select")
    if isinstance(select, str):
        select = [s.strip() for s in select.split(",") if s.strip()]
    if isinstance(select, list) and select:
        select = [str(s) for s in select]
        data = [_project(r, select) for r in data] if isinstance(data, list) else _project(data, select)
    out: dict = {"data": data}
    limit = int(result.get("max_items") or DEFAULT_MAX_ITEMS)
    if isinstance(data, list) and len(data) > limit:
        out = {"data": data[:limit], "truncated": True, "total_items": len(data)}
    return out


def lint_tools(entry: dict) -> list[str]:
    """Errors in a generic entry's tool definitions (the catalog lint adds them to its own checks)."""
    errs = []
    tools = (entry.get("adapter") or {}).get("tools")
    if not isinstance(tools, dict) or not tools:
        return ["adapter.tools must define at least one tool"]
    for name, tool in tools.items():
        where = f"tool {name}"
        if not TOOL_NAME_RE.match(str(name)):
            errs.append(f"{where}: a generic tool name must match [a-z][a-z0-9_]{{0,63}}")
        if not isinstance(tool, dict):
            errs.append(f"{where}: must be an object")
            continue
        for k in tool:
            if k not in TOOL_KEYS:
                errs.append(f"{where}: unknown key {k!r} for a generic tool")
        if not isinstance(tool.get("description"), str) or not tool["description"].strip():
            errs.append(f"{where}: description required (the operation's documented summary)")
        if not isinstance(tool.get("docs"), str) or not tool["docs"].startswith("https://"):
            errs.append(f"{where}: docs must cite the documented endpoint (an https URL)")
        if _method(tool) not in ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"):
            errs.append(f"{where}: unsupported method {tool.get('method')!r}")
        schema = tool.get("input", {"type": "object", "properties": {}})
        if not isinstance(schema, dict) or schema.get("type", "object") != "object" or not isinstance(schema.get("properties", {}), dict):
            errs.append(f"{where}: input must be a JSON Schema object with properties")
        else:
            req = schema.get("required", [])
            if not isinstance(req, list) or any(r not in schema.get("properties", {}) for r in req):
                errs.append(f"{where}: input.required must name input properties")
            if SELECT_ARG in schema.get("properties", {}):
                errs.append(f"{where}: {SELECT_ARG} is reserved (every read tool gets it)")
        if "cache_ttl" in tool and (not isinstance(tool["cache_ttl"], (int, float)) or isinstance(tool["cache_ttl"], bool)
                                or not 0 <= tool["cache_ttl"] <= 3600 or (tool["cache_ttl"] and not annotations(tool)["read_only"])):
            errs.append(f"{where}: cache_ttl must be 0-3600 seconds, and only on read tools (a write is never answered from a cache)")
        res = tool.get("result", {})
        if not isinstance(res, dict):
            errs.append(f"{where}: result must be an object")
        else:
            for k in res:
                if k not in RESULT_KEYS:
                    errs.append(f"{where}: unknown result key {k!r} (generic tools take {sorted(RESULT_KEYS)})")
            if "select" in res and (not isinstance(res["select"], list) or not all(isinstance(s, str) and s for s in res["select"])):
                errs.append(f"{where}: result.select must be a list of dotted paths")
            if "max_items" in res and (not isinstance(res["max_items"], int) or isinstance(res["max_items"], bool) or not 1 <= res["max_items"] <= 1000):
                errs.append(f"{where}: result.max_items must be an integer from 1 to 1000")
    return errs
