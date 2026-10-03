"""Call ONE read tool of a served entry through the Python runtime and show what happened: the request
the runtime sent (method, URL, query, body, non-secret headers), the raw response it parsed (truncated,
with a structure summary: keys, list lengths) and the mapped result or error. Authoring aid for
result paths: a list that comes back empty usually means `result.items` points at the wrong place,
or the platform answered another format (the runtime sends Accept: application/json).

Never calls a write tool (vocabulary read_only false). Credentials come from the environment.
Usage: platform-mcp-hub try [--max-chars N] <entry.json> <verb> '<json arguments>'
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from . import egress as egress_guard

SECRET_HEADERS = ("authorization", "cookie", "x-api-key", "api-key", "apikey", "token")


def structure(obj, depth: int = 0):
    """Keys and list lengths, five levels deep: enough to see where the records are."""
    if isinstance(obj, dict):
        if depth >= 5:
            return f"object({len(obj)} keys)"
        if len(obj) > 40:
            # an object keyed by id (Kraken's 600 pairs): a few keys and the shape of one value, not every key
            first = next(iter(obj.values()))
            return {"_keys": f"{len(obj)} keys, e.g. {', '.join(list(obj)[:5])}", "_value": structure(first, depth + 1)}
        return {k: structure(v, depth + 1) for k, v in obj.items()}
    if isinstance(obj, list):
        return [f"list({len(obj)})", structure(obj[0], depth + 1)] if obj else "list(0)"
    return type(obj).__name__


async def run(entry: dict, verb: str, args: dict, max_chars: int) -> dict:
    from . import credentials
    from .adapter import Adapter
    from .errors import PlatformError
    from .http import Transport
    from .vocab import vocab_for

    vocab = vocab_for(entry)
    a = entry["adapter"]
    if verb not in a["tools"]:
        return {"ok": False, "error": "invalid_input", "message": f"{entry['id']} does not map {verb}; mapped: {sorted(a['tools'])}"}
    if not vocab[verb].get("read_only"):
        return {"ok": False, "error": "invalid_input", "message": f"{verb} is a write tool; try_tool only calls read tools"}
    try:
        creds = credentials.resolve(entry["id"], a.get("auth", {"type": "none"}), a.get("config_fields"))
    except PlatformError as exc:
        return {"ok": False, "error": exc.kind, "message": str(exc)}
    pre = f"PLATFORM_MCP_{entry['id'].upper()}_"
    env = {k: v for k, v in os.environ.items() if k not in (pre + "ENV", pre + "BASE_URL")}  # try_tool calls the catalog's own base_url
    problems = await egress_guard.blocked(entry, env)
    if problems:  # an entry written from a hostile document must not make this tool read an intranet host
        return {"ok": False, "error": "blocked_host", "message": "; ".join(problems)}
    t = Transport(a["base_url"], {**a.get("auth", {"type": "none"}), "state_key": entry["id"]}, creds,
                  float(a.get("rate_per_second", 2)), f"platform-mcp/{entry['id']} try_tool", envelope=a.get("envelope"))
    t.fixed_headers = a.get("headers") or {}
    if a.get("error_kinds"):
        t.error_kinds = a["error_kinds"]  # the per-entry error table, as the served server applies it
    seen: dict = {}
    original = t.request

    async def capture(method, path, **kw):
        seen["request"] = {"method": method, "url": path if path.startswith("http") else a["base_url"] + path,
                           "params": {k: v for k, v in (kw.get("params") or {}).items() if v not in (None, "")} or None,
                           "body": kw.get("json"),
                           "headers": {k: v for k, v in {**t.fixed_headers, **(kw.get("headers") or {})}.items() if k.lower() not in SECRET_HEADERS} or None,
                           "default_accept": "application/json"}
        data = await original(method, path, **kw)
        seen["raw"] = data
        return data

    t.request = capture
    out: dict = {"verb": verb, "arguments": args}
    try:
        result = await Adapter(entry, t).call(verb, args)
        out.update(ok=True, result=result)
    except PlatformError as exc:
        out.update(ok=False, error=exc.kind, message=str(exc)[:600], http_status=getattr(exc, "status", None))
    finally:
        await t.aclose()
    out["request"] = seen.get("request")
    if "raw" in seen:
        text = json.dumps(seen["raw"], ensure_ascii=False, default=str)
        out["raw_structure"] = structure(seen["raw"])
        out["raw"] = text if len(text) <= max_chars else text[:max_chars] + f"… ({len(text)} chars)"
    if out.get("ok"):
        text = json.dumps(out["result"], ensure_ascii=False, default=str)
        if len(text) > max_chars:
            res = out["result"]
            lk = next((k for k, v in res.items() if isinstance(v, list)), None)
            out["result"] = {**{k: v for k, v in res.items() if k != lk}, lk: res[lk][:3], "_truncated": f"{len(res[lk])} records, first 3 shown"} if lk else text[:max_chars]
    return out


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    max_chars = 4000
    if "--max-chars" in argv:
        i = argv.index("--max-chars")
        max_chars = int(argv[i + 1])
        del argv[i:i + 2]
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    path, verb, raw_args = Path(argv[0]), argv[1], argv[2]
    try:
        entry = json.loads(path.read_text(encoding="utf-8"))
        args = json.loads(raw_args)
        if not isinstance(args, dict):
            raise ValueError("arguments must be a JSON object")
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": "invalid_input", "message": str(exc)}))
        return 1
    if not isinstance(entry.get("adapter"), dict):
        print(json.dumps({"ok": False, "error": "invalid_input", "message": f"{path} has no adapter block"}))
        return 1
    out = asyncio.run(run(entry, verb, args, max_chars))
    print(json.dumps(out, ensure_ascii=False, default=str))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
