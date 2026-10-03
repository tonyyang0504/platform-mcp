"""Registry metadata for one served catalog entry: servers/<category>/<id>/{server.json, manifest.json, README.md}.

There are no per-platform packages: every server runs from the one platform-mcp-hub package
(`platform-mcp-hub serve <id>`, Python on PyPI and TypeScript on npm). These files describe that command
to the MCP registry (server.json), to MCPB-capable desktop clients (manifest.json) and to people (README.md).
Edit the catalog, not these files; `python tools/gen_all.py` rewrites them."""

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.environ["PLATFORM_MCP_HUB_CATALOG"] = str(ROOT / "catalog")
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub import __version__ as HUB_VERSION  # noqa: E402
from platform_mcp_hub import catalog  # noqa: E402

ID_RE = re.compile(r"^[a-z0-9_]{1,60}$")
VERSION_RE = catalog.VERSION_RE
SCHEMA = "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json"
UNPUBLISHED = ("**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name "
               "from a registry until it is (anyone could register it first).")


def published() -> bool:
    return catalog.published()


def _args(ref: str) -> list[dict]:
    return [{"type": "positional", "value": "serve"}, {"type": "positional", "value": ref}]


def server_json(spec: dict) -> dict:
    """Registry entry: PyPI only. The registry verifies a PyPI package through `mcp-name:` lines in its README (the hub
    README lists every server); npm verifies through the single `mcpName` in package.json, which names the hub itself."""
    pid, cat = spec["id"], spec["category"]
    tools = spec["adapter"]["tools"]
    return {
        "$schema": SCHEMA,
        "name": catalog.registry_name(pid, cat),
        "description": (f"{spec.get('label') or pid} ({cat.replace('_', ' ')}): " + ", ".join(tools) + ". Every tool maps to a documented endpoint.")[:100],
        "version": HUB_VERSION,
        "repository": {"url": catalog.REPO_URL, "source": "github"},
        "websiteUrl": spec.get("docs_url"),
        "packages": [{"registryType": "pypi", "identifier": "platform-mcp-hub", "version": HUB_VERSION, "runtimeHint": "uvx",
                      "transport": {"type": "stdio"}, "packageArguments": _args(catalog.serve_ref(pid, cat)),
                      "environmentVariables": catalog.env_vars(spec)}],
    }


def manifest(spec: dict, sj: dict) -> dict:
    pid, cat = spec["id"], spec["category"]
    env_vars = catalog.env_vars(spec)
    return {
        "manifest_version": "0.2", "name": f"{catalog.slug(pid, cat)}-mcp", "display_name": f"{spec.get('label') or pid} MCP", "version": HUB_VERSION,
        "description": sj["description"], "author": {"name": "platform-mcp contributors"}, "license": "Apache-2.0",
        "server": {"type": "python", "entry_point": "platform-mcp-hub",
                   "mcp_config": {"command": "uvx", "args": ["platform-mcp-hub", "serve", catalog.serve_ref(pid, cat)],
                                  "env": {v["name"]: "${user_config." + v["name"].lower() + "}" for v in env_vars}}},
        "user_config": {v["name"].lower(): {"type": "string", "title": v["name"], "description": v["description"], "sensitive": v["isSecret"], "required": v["isRequired"],
                                            **({"default": v["default"]} if "default" in v else {})} for v in env_vars},
        "tools": [{"name": t, "description": spec["adapter"]["tools"][t].get("note", "")} for t in spec["adapter"]["tools"]],
    }


def readme(spec: dict, sj: dict) -> str:
    pid, cat = spec["id"], spec["category"]
    tools = spec["adapter"]["tools"]
    ref = catalog.serve_ref(pid, cat)
    out = [f"# {spec.get('label') or pid} MCP server", "", f"Category: **{cat}** · Docs: {spec.get('docs_url')} · Verified: {spec.get('verified_at')}", "",
           f"Served by [platform-mcp-hub]({catalog.REPO_URL}) from `catalog/{cat}/{pid}.json`; edit the catalog, not this file.", "", "## Tools", ""]
    for t, ts in tools.items():
        out.append(f"- `{t}` — `{ts.get('method', 'GET')} {ts.get('path')}` ({ts.get('docs') or spec.get('docs_url')})")
    for t, why in spec["adapter"].get("not_offered", {}).items():
        out.append(f"- ~~`{t}`~~ not offered: {why}")
    out += ["", "## Credentials", ""] + ([f"- `{v['name']}` — {v['description']}" for v in sj["packages"][0]["environmentVariables"]] or ["None."])
    out += ["", "## Run", ""]
    if published():
        out += [f"    uvx platform-mcp-hub serve {ref}          # Python", f"    npx -y platform-mcp-hub serve {ref}       # TypeScript",
                f"    claude mcp add {pid} -- uvx platform-mcp-hub serve {ref}"]
    else:
        out += [UNPUBLISHED, "", f"    uvx --from git+{catalog.REPO_URL} platform-mcp-hub serve {ref}   # Python, stdio",
                f"    git clone {catalog.REPO_URL} && cd platform-mcp && uv run platform-mcp-hub serve {ref}",
                f"    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve {ref}   # TypeScript"]
    out += ["", f"Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `{sj['name']}`. Python and TypeScript serve identical tools."]
    return "\n".join(out) + "\n"


def generate(entry: Path) -> Path:
    spec = json.loads(entry.read_text(encoding="utf-8"))
    if "adapter" not in spec:
        raise SystemExit(f"{entry}: no adapter block; nothing to generate")
    pid, cat = spec.get("id"), spec.get("category")
    version = spec.get("version", "0.1.0")
    # these name directories and land in JSON/Markdown: refuse anything that is not a plain name or version
    if not isinstance(pid, str) or not ID_RE.match(pid) or not isinstance(cat, str) or not ID_RE.match(cat):
        raise SystemExit(f"{entry}: id and category must match [a-z0-9_]{{1,60}}")
    if not isinstance(version, str) or not VERSION_RE.match(version):
        raise SystemExit(f"{entry}: version must be MAJOR.MINOR.PATCH (got {version!r})")
    base = ROOT / "servers" / cat / pid
    base.mkdir(parents=True, exist_ok=True)
    sj = server_json(spec)
    (base / "server.json").write_text(json.dumps(sj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (base / "manifest.json").write_text(json.dumps(manifest(spec, sj), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (base / "README.md").write_text(readme(spec, sj), encoding="utf-8")
    return base


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        print("generated", generate(Path(arg)))
