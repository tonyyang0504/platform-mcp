"""The catalog that ships with platform-mcp-hub: where it lives, how entries are found, and the facts every
front end (the CLI, the directory server, the registry metadata) derives from an entry. The TypeScript
runtime's catalog.ts implements the same lookups; tests/test_cli_python.py and tests/cli.typescript.test.mjs
hold both to the same answers.

Lookup order for the catalog directory:
  1. PLATFORM_MCP_HUB_CATALOG (a directory with schema/vocab.json)
  2. the copy installed inside the package (platform_mcp_hub/catalog, wheels and sdists)
  3. the repository checkout this module lives in (<repo>/catalog)
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Iterator

PKG_DIR = Path(__file__).resolve().parent
REPO_DIR = PKG_DIR.parents[2]  # runtime/python/platform_mcp_hub -> <repo>
NOT_CATEGORIES = ("schema", "sources")
ID_RE = re.compile(r"^[a-z0-9_]{1,60}$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
CATALOG_ENV = "PLATFORM_MCP_HUB_CATALOG"
REPO_URL = "https://github.com/tonyyang0504/platform-mcp"
REGISTRY_PREFIX = "io.github.tonyyang0504"


class EntryError(ValueError):
    """A lookup or validation problem, phrased for the person at the terminal."""


def _is_catalog(p: Path) -> bool:
    return (p / "schema" / "vocab.json").is_file()


def catalog_dir() -> Path:
    env = os.environ.get(CATALOG_ENV)
    if env:
        p = Path(env).expanduser()
        if not _is_catalog(p):
            raise EntryError(f"{CATALOG_ENV}={env} is not a catalog directory (no schema/vocab.json)")
        return p.resolve()
    for p in (PKG_DIR / "catalog", REPO_DIR / "catalog"):
        if _is_catalog(p):
            return p
    raise EntryError("no catalog found: reinstall platform-mcp-hub, or set PLATFORM_MCP_HUB_CATALOG to a checkout's catalog/ directory")


def is_checkout() -> bool:
    """True when this module runs from a repository checkout (tools/ and generators/ beside the catalog)."""
    return _is_catalog(REPO_DIR / "catalog") and (REPO_DIR / "runtime" / "python" / "platform_mcp_hub").is_dir()


@lru_cache(maxsize=4)
def _vocab(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def vocab() -> dict:
    return _vocab(str(catalog_dir() / "schema" / "vocab.json"))


def release() -> dict:
    try:
        return json.loads((catalog_dir() / "schema" / "release.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, EntryError):
        return {}


def published() -> bool:
    """catalog/schema/release.json: true only once the operator has published platform-mcp-hub to PyPI and npm."""
    return release().get("published") is True


def contract_text() -> str:
    """The adapter contract (docs/ADAPTER_CONTRACT.md), shipped inside the package for tools that author entries."""
    for p in (PKG_DIR / "ADAPTER_CONTRACT.md", REPO_DIR / "docs" / "ADAPTER_CONTRACT.md"):
        if p.is_file():
            return p.read_text(encoding="utf-8")
    return ""


def entry_files(root: Path | None = None) -> Iterator[Path]:
    root = root or catalog_dir()
    for p in sorted(root.glob("*/*.json")):
        if p.parent.name not in NOT_CATEGORIES:
            yield p


def iter_entries(served_only: bool = False, root: Path | None = None) -> Iterator[tuple[Path, dict]]:
    for p in entry_files(root):
        try:
            e = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(e, dict):
            continue
        if served_only and not isinstance(e.get("adapter"), dict):
            continue
        yield p, e


def served_categories(pid: str, root: Path | None = None) -> list[str]:
    root = root or catalog_dir()
    out = []
    for p in sorted(root.glob(f"*/{pid}.json")):
        if p.parent.name in NOT_CATEGORIES:
            continue
        try:
            if isinstance(json.loads(p.read_text(encoding="utf-8")).get("adapter"), dict):
                out.append(p.parent.name)
        except (OSError, ValueError):
            continue
    return out


def find(ref: str, category: str | None = None) -> tuple[Path, dict]:
    """A served entry by `id`, `category/id`, or `id` + category. An id served in several categories needs the category."""
    ref = (ref or "").strip()
    if "/" in ref:
        category, _, ref = ref.partition("/")
    if not ID_RE.match(ref) or (category is not None and (not ID_RE.match(category) or category in NOT_CATEGORIES)):
        raise EntryError(f"not a platform id: {json.dumps(ref)} (lowercase [a-z0-9_]; `platform-mcp-hub list` shows them)")
    cats = served_categories(ref)
    if category:
        if category not in cats:
            hint = f"; it is served in: {', '.join(cats)}" if cats else ""
            raise EntryError(f"no served entry {category}/{ref}{hint}")
    elif not cats:
        raise EntryError(f"no served entry {json.dumps(ref)}; `platform-mcp-hub list` shows the {sum(1 for _ in iter_entries(True))} served platforms")
    elif len(cats) > 1:
        raise EntryError(f"{json.dumps(ref)} is served in several categories ({', '.join(cats)}): use <category>/{ref}, e.g. {cats[0]}/{ref}")
    else:
        category = cats[0]
    p = catalog_dir() / category / f"{ref}.json"
    return p, json.loads(p.read_text(encoding="utf-8"))


def validate_entry(entry: object) -> list[str]:
    """The structural checks `serve --entry` makes before serving a file (identical in catalog.ts). The full
    evidence lint is `platform-mcp-hub lint`; this only refuses what would not run or would run unsafely."""
    if not isinstance(entry, dict):
        return ["the entry must be a JSON object"]
    errs = []
    pid, cat = entry.get("id"), entry.get("category")
    if not isinstance(pid, str) or not ID_RE.match(pid):
        errs.append("id must match [a-z0-9_]{1,60}")
    voc = vocab()
    generic = cat == "generic"
    if not generic and (not isinstance(cat, str) or cat not in voc or not isinstance(voc.get(cat), dict)):
        errs.append(f"category must be generic or one of: {', '.join(sorted(k for k, v in voc.items() if isinstance(v, dict)))}")
    a = entry.get("adapter")
    if not isinstance(a, dict):
        errs.append("no adapter block: only served entries (with `adapter`) can be served")
        return errs
    if not isinstance(a.get("base_url"), str) or not a["base_url"].startswith("https://"):
        errs.append("adapter.base_url must be an https URL")
    tools = a.get("tools")
    if not isinstance(tools, dict) or not tools:
        errs.append("adapter.tools must map at least one verb")
    elif generic:
        from .generic import TOOL_NAME_RE
        bad = sorted(n for n, t in tools.items() if not TOOL_NAME_RE.match(str(n)) or not isinstance(t, dict)
                     or not isinstance(t.get("input", {}), dict))
        if bad:
            errs.append(f"generic tools need a name matching [a-z][a-z0-9_]{{0,63}} and an object input schema: {', '.join(bad)}")
    elif isinstance(cat, str) and isinstance(voc.get(cat), dict):
        unknown = sorted(v for v in tools if v not in voc[cat])
        if unknown:
            errs.append(f"verbs not in the {cat} vocabulary: {', '.join(unknown)}")
    version = entry.get("version", "0.1.0")
    if not isinstance(version, str) or not VERSION_RE.match(version):
        errs.append("version must be MAJOR.MINOR.PATCH")
    return errs


def load_entry_file(path: str | Path) -> dict:
    p = Path(path).expanduser()
    try:
        entry = json.loads(p.read_text(encoding="utf-8"))
    except OSError as exc:
        raise EntryError(f"cannot read {p}: {exc.strerror or exc}")
    except ValueError as exc:
        raise EntryError(f"{p} is not valid JSON: {exc}")
    errs = validate_entry(entry)
    if errs:
        raise EntryError(f"{p}: " + "; ".join(errs))
    return entry


def serve_ref(pid: str, category: str) -> str:
    """What to pass to `serve`: the bare id, or category/id when the id is served in several categories."""
    return f"{category}/{pid}" if len(served_categories(pid)) > 1 else pid


def slug(pid: str, category: str) -> str:
    """Registry name stem: an id served in several categories gets the category appended, so names never collide."""
    return f"{pid}-{category.replace('_', '-')}" if len(served_categories(pid)) > 1 else pid


def registry_name(pid: str, category: str) -> str:
    return f"{REGISTRY_PREFIX}/{slug(pid, category)}-mcp"


def _where(e: dict) -> str:
    if e.get("base_url"):
        return e["base_url"]
    if e.get("hosts"):
        return "hosts " + ", ".join(e["hosts"].values())
    if e.get("same_host"):
        return "production host with test accounts or test keys"
    return "production host with environment headers"


def env_vars(entry: dict) -> list[dict]:
    """Every PLATFORM_MCP_<ID>_* variable the entry reads: credentials (secret), per-install config, and the
    environment selector + base URL override when the entry declares vendor environments."""
    pid, a = entry["id"], entry["adapter"]
    pre = f"PLATFORM_MCP_{pid.upper()}_"
    out = [{"name": pre + f["name"].upper(), "description": f.get("help", f["name"]), "isRequired": f.get("required", True), "isSecret": True}
           for f in (a.get("auth") or {}).get("fields", []) if isinstance(f, dict)]
    out += [{"name": pre + f["name"].upper(), "description": f.get("help", f["name"]), "isRequired": f.get("required", False), "isSecret": False}
            for f in a.get("config_fields") or [] if isinstance(f, dict)]
    envs = a.get("environments") or {}
    if envs:
        desc = ("Vendor environment (default production): " + "; ".join(f"{n} = {_where(envs[n])}" for n in sorted(envs))
                + ". Credentials are the environment's own; see adapter.environments in the catalog entry.")
        out += [
            {"name": pre + "ENV", "description": desc, "isRequired": False, "isSecret": False, "default": "production", "choices": ["production", *sorted(envs)]},
            {"name": pre + "BASE_URL", "description": "Optional https base URL override (a mock or a private gateway); replaces the selected environment's base_url. Never echoed in errors.",
             "isRequired": False, "isSecret": False},
        ]
    return out


def run_commands(pid: str, category: str) -> dict:
    """How to start one server: from the registries once published, from source until then (never `uvx <name>`
    before the name is ours: anyone could register it first)."""
    ref = serve_ref(pid, category)
    if published():
        return {"uvx": f"uvx platform-mcp-hub serve {ref}", "npx": f"npx -y platform-mcp-hub serve {ref}",
                "claude_code": f"claude mcp add {pid} -- uvx platform-mcp-hub serve {ref}",
                "http": f"uvx platform-mcp-hub serve {ref} --http --port 8000"}
    return {"status": "unpublished",
            "python": f"uvx --from git+{REPO_URL} platform-mcp-hub serve {ref}",
            "checkout": f"git clone {REPO_URL} && cd platform-mcp && uv run platform-mcp-hub serve {ref}",
            "typescript": f"cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve {ref}",
            "http": f"uv run platform-mcp-hub serve {ref} --http --port 8000"}


def describe(entry: dict) -> dict:
    a = entry["adapter"]
    pid, cat = entry["id"], entry["category"]
    return {
        "id": pid, "category": cat, "label": entry.get("label") or pid, "version": entry.get("version", "0.1.0"),
        "docs_url": entry.get("docs_url"), "verified_at": entry.get("verified_at"),
        "tools": {v: {"method": t.get("method", "GET"), "path": t.get("path"), "docs": t.get("docs") or entry.get("docs_url")} for v, t in a["tools"].items()},
        "not_offered": a.get("not_offered") or {},
        "auth": (a.get("auth") or {}).get("type", "none"),
        "env": env_vars(entry),
        "live_check": entry.get("live_check"),
        "serve": serve_ref(pid, cat), "registry_name": registry_name(pid, cat),
        "run": run_commands(pid, cat),
    }
