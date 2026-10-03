"""Offline stdio smoke of one served entry, in both languages (`platform-mcp-hub serve --entry`), exactly as an MCP client starts it:
initialize, tools/list, then check that the tools are exactly the adapter's mapped verbs and that every
tool has a title, a read-only or destructive annotation, an input schema and an output schema. No tool
is called (no network). Used by the forge's test_server.

Usage: platform-mcp-hub smoke [--json] [--lang py|ts|both] <entry.json>
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

from . import launch


async def smoke(entry: dict, lang: str, scratch: Path, path: Path) -> dict:
    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    out: dict = {"lang": lang, "ok": False, "problems": []}
    try:
        cmd, extra = launch.python_serve(path) if lang == "py" else launch.ts_serve(path)
    except SystemExit as exc:
        out["problems"].append(str(exc))
        return out
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", "/tmp"), **extra}
    errlog = open(scratch / f"{entry['id']}.{lang}.smoke.stderr.log", "w+")
    try:
        async with stdio_client(StdioServerParameters(command=cmd[0], args=cmd[1:], env=env), errlog=errlog) as (r, w):
            async with ClientSession(r, w) as s:
                init = await asyncio.wait_for(s.initialize(), 60)
                tools = (await asyncio.wait_for(s.list_tools(), 60)).tools
    except Exception as exc:  # a server that does not start is exactly what this smoke is for
        errlog.seek(0)
        tail = errlog.read()[-600:]
        out["problems"].append(f"server did not start: {exc.__class__.__name__}: {exc}"[:300] + (f" | stderr: {tail}" if tail else ""))
        return out
    out["server"] = init.server_info.name
    out["protocol"] = init.protocol_version
    names = [t.name for t in tools]
    out["tools"] = names
    expected = list(entry["adapter"]["tools"])
    if sorted(names) != sorted(expected):
        out["problems"].append(f"tools {sorted(names)} differ from the adapter's verbs {sorted(expected)}")
    for t in tools:
        ann = t.annotations
        if not t.title:
            out["problems"].append(f"{t.name}: no title")
        if not ann or (ann.read_only_hint is None and ann.destructive_hint is None):
            out["problems"].append(f"{t.name}: neither readOnlyHint nor destructiveHint")
        if not t.input_schema or t.input_schema.get("type") != "object":
            out["problems"].append(f"{t.name}: no object input schema")
        if not t.output_schema:
            out["problems"].append(f"{t.name}: no output schema")
    out["ok"] = not out["problems"]
    return out


async def main_async(path: Path, langs: list[str]) -> dict:
    entry = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(entry.get("adapter"), dict):
        return {"ok": False, "runs": [], "problems": [f"{path}: no adapter block"]}
    with tempfile.TemporaryDirectory(prefix="smoke-entry-") as tmp:
        runs = [await smoke(entry, lang, Path(tmp), path.resolve()) for lang in langs]
    return {"ok": all(r["ok"] for r in runs), "runs": runs}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]
    lang = "both"
    if "--lang" in argv:
        i = argv.index("--lang")
        lang = argv[i + 1]
        del argv[i:i + 2]
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    path = Path(argv[0])
    if not path.is_file():
        rep = {"ok": False, "runs": [], "problems": [f"no such entry file {path}"]}
    else:
        rep = asyncio.run(main_async(path, ["py", "ts"] if lang == "both" else [lang]))
    if as_json:
        print(json.dumps(rep, ensure_ascii=False))
    else:
        for r in rep.get("runs", []):
            print(f"{r['lang']}: {'ok' if r['ok'] else 'FAIL'} tools={r.get('tools')} " + "; ".join(r["problems"]))
        for p in rep.get("problems", []):
            print(p)
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
