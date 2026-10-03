"""platform-mcp-hub command line. The serving commands (list, describe, serve, directory) behave identically in
the TypeScript CLI (`npx platform-mcp-hub ...`); the authoring tools (lint, try, smoke, verify) are Python only.

    platform-mcp-hub list [--category C] [--query TEXT] [--json]
    platform-mcp-hub describe <id | category/id> [--category C]      (JSON)
    platform-mcp-hub describe --entry my_entry.json
    platform-mcp-hub serve <id | category/id> [--category C] [--http [--host H] [--port N] [--allow-remote]]
    platform-mcp-hub serve --entry my_entry.json [--http ...]
    platform-mcp-hub directory [--http [--host H] [--port N] [--allow-remote]]
    platform-mcp-hub lint [--json] [entry.json ...]
    platform-mcp-hub try [--max-chars N] <entry.json | id> <verb> '<json arguments>'
    platform-mcp-hub smoke [--json] [--lang py|ts|both] <entry.json | id>
    platform-mcp-hub verify [--only id,...] [--entry file] [--lang py|ts|both] ...   (live calls; see --help)

Credentials always come from PLATFORM_MCP_<ID>_<FIELD> environment variables; `describe` lists them.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from . import __version__, catalog

SERVE_FLAGS_WITH_VALUE = ("--host", "--port", "--category", "--entry")


def _fail(msg: str, code: int = 2) -> int:
    print(f"platform-mcp-hub: {msg}", file=sys.stderr)
    return code


def _pop(argv: list[str], flag: str) -> str | None:
    if flag in argv:
        i = argv.index(flag)
        if i + 1 >= len(argv):
            raise catalog.EntryError(f"{flag} needs a value")
        value = argv[i + 1]
        del argv[i:i + 2]
        return value
    return None


def _resolve(argv: list[str]) -> tuple[Path, dict]:
    """--entry FILE, or a positional <id | category/id> with an optional --category. Consumes what it reads."""
    entry = _pop(argv, "--entry")
    category = _pop(argv, "--category")
    if entry:
        p = Path(os.path.abspath(os.path.expanduser(entry)))  # as typed (like path.resolve in cli.ts), symlinks kept
        return p, catalog.load_entry_file(p)
    refs = [a for a in argv if not a.startswith("-")]
    if not refs:
        raise catalog.EntryError("name a platform (`platform-mcp-hub list`) or pass --entry <file.json>")
    argv.remove(refs[0])
    return catalog.find(refs[0], category)


def _list_rows(category: str | None, query: str | None) -> list[dict]:
    rows = []
    q = (query or "").lower().split()
    for _, e in catalog.iter_entries(served_only=True):
        if category and e["category"] != category:
            continue
        hay = " ".join(str(e.get(k) or "") for k in ("id", "label", "category", "docs_url", "url")).lower()
        if q and not all(t in hay for t in q):
            continue
        rows.append({"id": e["id"], "category": e["category"], "label": e.get("label") or e["id"],
                     "serve": catalog.serve_ref(e["id"], e["category"]), "tools": list(e["adapter"]["tools"]),
                     "auth": (e["adapter"].get("auth") or {}).get("type", "none")})
    return rows


def cmd_list(argv: list[str]) -> int:
    as_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]
    category, query = _pop(argv, "--category"), _pop(argv, "--query")
    if argv:
        return _fail(f"unexpected arguments: {' '.join(argv)}")
    rows = _list_rows(category, query)
    if as_json:
        print(json.dumps({"total": len(rows), "items": rows}, ensure_ascii=False))
        return 0
    width = max((len(r["serve"]) for r in rows), default=10)
    for r in rows:
        print(f"{r['serve']:<{width}}  {r['category']:<20} {r['label'][:40]:<40}  {', '.join(r['tools'])}")
    print(f"{len(rows)} served platforms; `platform-mcp-hub describe <id>` for credentials and run commands", file=sys.stderr)
    return 0


def cmd_describe(argv: list[str]) -> int:
    path, entry = _resolve(argv)
    if argv:
        return _fail(f"unexpected arguments: {' '.join(argv)}")
    print(json.dumps(catalog.describe(entry), indent=1, ensure_ascii=False))
    return 0


def cmd_serve(argv: list[str]) -> int:
    path, entry = _resolve(argv)
    from .server import main as serve_main
    serve_main(entry, argv)  # --http / --host / --port / --allow-remote; stdio otherwise
    return 0


def cmd_directory(argv: list[str]) -> int:
    import argparse
    import asyncio

    from . import directory
    from .server import TOKEN_ENV, _serve, http_auth_token
    ap = argparse.ArgumentParser(prog="platform-mcp-hub directory", description="Directory MCP server over the whole catalog")
    ap.add_argument("--http", action="store_true", help="serve Streamable HTTP instead of stdio")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--allow-remote", action="store_true", help=f"allow a non-loopback --host (also requires {TOKEN_ENV})")
    args = ap.parse_args(argv)
    if args.http:
        try:
            token = http_auth_token(args.host, args.allow_remote)
        except ValueError as exc:
            return _fail(str(exc))
        _serve(directory.build_http_app(args.host, token), args.host, args.port)
    else:
        asyncio.run(directory.build_server().run_stdio_async())
    return 0


def _entry_arg(argv: list[str], index_from_end: int) -> list[str]:
    """try/smoke take an entry file; accept a catalog id there too."""
    if len(argv) >= index_from_end:
        i = len(argv) - index_from_end
        if not Path(argv[i]).expanduser().is_file() and not argv[i].endswith(".json"):
            argv[i] = str(catalog.find(argv[i])[0])
    return argv


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__.strip())
        return 0 if argv else 2
    if argv[0] in ("-V", "--version", "version"):
        print(f"platform-mcp-hub {__version__}")
        return 0
    cmd, rest = argv[0], argv[1:]
    try:
        if cmd == "list":
            return cmd_list(rest)
        if cmd == "describe":
            return cmd_describe(rest)
        if cmd == "serve":
            return cmd_serve(rest)
        if cmd == "directory":
            return cmd_directory(rest)
        if cmd == "lint":
            from . import lint
            return lint.main(rest)
        if cmd == "try":
            from . import trytool
            return trytool.main(_entry_arg(rest, 3))
        if cmd == "smoke":
            from . import smoke
            return smoke.main(_entry_arg(rest, 1))
        if cmd == "verify":
            from . import live_verify
            return live_verify.main(rest)
    except catalog.EntryError as exc:
        return _fail(str(exc))
    return _fail(f"unknown command {json.dumps(cmd)}; run `platform-mcp-hub --help`")


def entry() -> None:
    sys.exit(main())
