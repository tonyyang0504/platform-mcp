"""How the verification tools start one server over stdio, exactly as an MCP client would: the Python CLI of this
very package (`python -m platform_mcp_hub serve --entry <file>`) and the TypeScript CLI (`node <cli.js> serve
--entry <file>`). Both children get the same catalog (PLATFORM_MCP_HUB_CATALOG), so they serve the same verbs.

The TypeScript CLI is found at PLATFORM_MCP_HUB_TS_CLI, else in this checkout (runtime/typescript/dist/cli.js),
else in a global npm install of platform-mcp-hub. Without one, the TypeScript half is unavailable (and says so)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import catalog

TS_CLI_ENV = "PLATFORM_MCP_HUB_TS_CLI"


def _child_env() -> dict:
    """PYTHONPATH that imports this same platform_mcp_hub, and the catalog this process uses."""
    pkg_parent = str(Path(__file__).resolve().parents[1])
    pp = [pkg_parent] + [p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p and p != pkg_parent]
    return {"PYTHONPATH": os.pathsep.join(pp), catalog.CATALOG_ENV: str(catalog.catalog_dir())}


def python_serve(entry_path: str | Path) -> tuple[list[str], dict]:
    return [sys.executable, "-m", "platform_mcp_hub", "serve", "--entry", str(entry_path)], _child_env()


def ts_cli() -> Path | None:
    env = os.environ.get(TS_CLI_ENV)
    if env:
        p = Path(env).expanduser()
        return p if p.is_file() else None
    local = catalog.REPO_DIR / "runtime" / "typescript" / "dist" / "cli.js"
    if catalog.is_checkout() and local.is_file():
        return local
    npm = shutil.which("npm")
    if npm:
        try:
            root = subprocess.run([npm, "root", "-g"], capture_output=True, text=True, timeout=30).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            root = ""
        p = Path(root) / "platform-mcp-hub" / "dist" / "cli.js" if root else None
        if p and p.is_file():
            return p
    return None


def ts_missing_reason() -> str:
    if not shutil.which("node"):
        return "node is not on PATH"
    if catalog.is_checkout():
        return "runtime/typescript is not built (cd runtime/typescript && npm ci --ignore-scripts && npm run build)"
    return f"no TypeScript runtime found: npm install -g platform-mcp-hub, or set {TS_CLI_ENV} to its dist/cli.js"


def ts_serve(entry_path: str | Path) -> tuple[list[str], dict]:
    cli = ts_cli()
    if cli is None or not shutil.which("node"):
        raise SystemExit(f"TypeScript unavailable: {ts_missing_reason()}")
    return ["node", str(cli), "serve", "--entry", str(entry_path)], {catalog.CATALOG_ENV: str(catalog.catalog_dir())}
