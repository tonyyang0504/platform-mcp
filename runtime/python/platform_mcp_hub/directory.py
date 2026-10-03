"""Directory MCP server (`platform-mcp-hub directory`): which platforms exist per category, which have an API,
which are served by platform-mcp-hub, what each can do, and how to run it. The TypeScript runtime's
directory.ts is the same server over the same snapshot (catalog/directory.json, written by tools/build_directory.py)."""

import json
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from . import __version__, catalog

_DATA: dict[str, Any] | None = None
REPO = catalog.REPO_URL


def data() -> dict[str, Any]:
    """The compact snapshot of the whole catalog that ships with the package."""
    global _DATA
    if _DATA is None:
        _DATA = json.loads((catalog.catalog_dir() / "directory.json").read_text(encoding="utf-8"))
    return _DATA


def _summary(p: dict) -> dict:
    return {k: p.get(k) for k in ("id", "category", "label", "lane", "has_api", "served", "tools", "url", "docs_url", "regions")}


def _match(p: dict, *, category: str | None, query: str | None, served_only: bool, has_api: bool | None, region: str | None) -> bool:
    if category and p["category"] != category:
        return False
    if served_only and not p["served"]:
        return False
    if has_api is True and p.get("has_api") != "yes":
        return False
    if has_api is False and p.get("has_api") == "yes":
        return False
    if region and region.lower() not in [str(r).lower() for r in (p.get("regions") or [])]:
        return False
    if query:
        hay = " ".join(str(p.get(k) or "") for k in ("id", "label", "url", "docs_url", "kind")).lower() + " " + " ".join(p.get("capabilities") or []).lower()
        return all(tok in hay for tok in query.lower().split())
    return True


UNPUBLISHED = ("Unpublished: platform-mcp-hub is not on PyPI or npm yet; run it from source "
               "(never `uvx`/`npx` the name before it is published: anyone could register it first).")


def install_hints(p: dict) -> dict:
    """How to run one served platform. Identical to installHints in directory.ts."""
    env = {c["env"]: "<value>" for c in p.get("credentials") or []}
    ref = p.get("serve") or p["id"]
    hints: dict[str, Any] = {"env": env, "serve": f"platform-mcp-hub serve {ref}"}
    if not (data().get("snapshot") or {}).get("published"):
        # catalog/schema/release.json is false until the operator publishes (docs/RELEASE_CHECKLIST.md)
        hints["status"] = "unpublished"
        hints["warning"] = UNPUBLISHED
        hints["from_source"] = {
            "python": f"uvx --from git+{REPO} platform-mcp-hub serve {ref}",
            "checkout": f"git clone {REPO} && cd platform-mcp && uv run platform-mcp-hub serve {ref}",
            "typescript": f"cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve {ref}",
        }
    else:
        hints["uvx"] = f"uvx platform-mcp-hub serve {ref}"
        hints["npx"] = f"npx -y platform-mcp-hub serve {ref}"
        hints["claude_code"] = f"claude mcp add {p['id']} -- uvx platform-mcp-hub serve {ref}"
        hints["claude_desktop"] = {"mcpServers": {p["id"]: {"command": "uvx", "args": ["platform-mcp-hub", "serve", ref], "env": env}}}
    hints["http"] = f"platform-mcp-hub serve {ref} --http --port 8000  # Streamable HTTP on http://127.0.0.1:8000/mcp"
    hints["source"] = f"{REPO}/blob/main/catalog/{p['category']}/{p['id']}.json"
    return hints


def build_server() -> MCPServer:
    d = data()
    n_served = sum(c["served"] for c in d["categories"])
    server = MCPServer(
        name="platform-mcp-hub-directory", title="platform-mcp-hub directory", version=__version__,
        instructions=(
            f"Directory of {len(d['platforms'])} platforms in {len(d['categories'])} categories "
            f"({', '.join(c['category'] for c in d['categories'])}); {n_served} of them are served by platform-mcp-hub. "
            "Use list_categories to orient, list_platforms to browse or search, search_capabilities to find platforms "
            "that support a verb (e.g. `search`, `publish_text`, `place_order`), and describe_platform for the tool list, "
            "credential environment variables and install commands. Tools are read-only over a bundled snapshot."
        ),
    )
    ro = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)

    def list_categories() -> dict[str, Any]:
        """Categories with platform counts, how many have a documented API and how many ship a ready MCP server, plus each category's shared verb vocabulary."""
        return {"categories": [{**c, "verbs": sorted(d["verbs"].get(c["category"], {}))} for c in d["categories"]], "snapshot": d["snapshot"]}

    def list_platforms(category: str | None = None, query: str | None = None, served_only: bool = False, has_api: bool | None = None, region: str | None = None, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        """Browse or search platforms. Filter by category, free-text query (id, label, url, capabilities), served_only (ready MCP server), has_api, region; paginate with limit/offset."""
        limit = max(1, min(int(limit), 200))
        rows = [p for p in d["platforms"] if _match(p, category=category, query=query, served_only=served_only, has_api=has_api, region=region)]
        return {"total": len(rows), "offset": offset, "limit": limit, "items": [_summary(p) for p in rows[offset: offset + limit]]}

    def describe_platform(platform_id: str) -> dict[str, Any]:
        """Everything the directory knows about one platform: API facts, tools it offers (and the verbs it does not, with reasons), credential env vars, package names and install commands."""
        for p in d["platforms"]:
            if p["id"] == platform_id:
                out = dict(p)
                out["verbs"] = {v: d["verbs"].get(p["category"], {}).get(v) for v in p.get("tools") or []}
                if p["served"]:
                    out["install"] = install_hints(p)
                else:
                    out["how_to_add"] = f"Not served yet. Author an adapter block for catalog/{p['category']}/{p['id']}.json (see {REPO}/blob/main/docs/ADAPTER_CONTRACT.md)."
                return out
        return {"error": "not_found", "message": f"no platform with id {platform_id!r}; try list_platforms(query=...)"}

    def search_capabilities(capability: str, category: str | None = None, served_only: bool = False, limit: int = 50) -> dict[str, Any]:
        """Platforms that support a verb (a served tool name such as `search`, `publish_text`, `get_ticker`) or a catalogued capability keyword (e.g. `job_search`, `webhooks`)."""
        cap = capability.lower().strip()
        limit = max(1, min(int(limit), 200))
        rows = []
        for p in d["platforms"]:
            if category and p["category"] != category:
                continue
            if served_only and not p["served"]:
                continue
            tools = [t.lower() for t in p.get("tools") or []]
            caps = [c.lower() for c in p.get("capabilities") or []]
            if cap in tools or any(cap in c for c in caps):
                rows.append({**_summary(p), "matched": "tool" if cap in tools else "capability"})
        rows.sort(key=lambda r: (not r["served"], r["category"], r["id"]))
        return {"capability": capability, "total": len(rows), "items": rows[:limit]}

    for fn, title in ((list_categories, "List categories"), (list_platforms, "List or search platforms"), (describe_platform, "Describe a platform"), (search_capabilities, "Search by capability")):
        server.add_tool(fn, name=fn.__name__, title=title, description=fn.__doc__, structured_output=True, annotations=ToolAnnotations(title=title, **{k: v for k, v in ro.model_dump().items() if k != "title"}))
    return server


def build_http_app(host: str = "127.0.0.1", token: str | None = None):
    from .server import BearerAuth
    app = build_server().streamable_http_app(stateless_http=True, host=host)
    return BearerAuth(app, token) if token else app
