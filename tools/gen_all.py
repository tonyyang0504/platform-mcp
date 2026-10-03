"""Regenerate everything derived from the catalog (CI fails when the result differs from what is committed):

  servers/<category>/<id>/{server.json, manifest.json, README.md}   registry metadata per served entry
  servers/directory/{server.json, manifest.json}                     registry metadata of the hub itself
  runtime/python/README.md                                          the PyPI page (lists every registry name)
  catalog/index.json                                                counts per category
  catalog/directory.json                                            the directory server's snapshot
"""
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["PLATFORM_MCP_HUB_CATALOG"] = str(ROOT / "catalog")
sys.path.insert(0, str(ROOT / "generators" / "python"))
sys.path.insert(0, str(ROOT / "tools"))
import build_directory  # noqa: E402
import gen  # noqa: E402
from platform_mcp_hub import __version__, catalog  # noqa: E402

served = [(p, e) for p, e in catalog.iter_entries(served_only=True, root=ROOT / "catalog")]
keep = set()
for p, e in served:
    keep.add(gen.generate(p))
# a platform that is no longer served (or was renamed) loses its metadata directory
for d in sorted((ROOT / "servers").glob("*/*")):
    if d.is_dir() and d.parent.name != "directory" and d not in keep:
        shutil.rmtree(d)
for d in sorted((ROOT / "servers").glob("*")):
    if d.is_dir() and not any(d.iterdir()):
        d.rmdir()
print(f"regenerated registry metadata for {len(served)} servers")

# the hub's own registry entry: `platform-mcp-hub directory` (PyPI and npm; npm's package.json mcpName names it)
hub = ROOT / "servers" / "directory"
hub.mkdir(parents=True, exist_ok=True)
hub_name = f"{catalog.REGISTRY_PREFIX}/platform-mcp-hub"
desc = "Directory of 3,400+ platforms with 450+ ready MCP servers: browse, search by capability, get run commands."
(hub / "server.json").write_text(json.dumps({
    "$schema": gen.SCHEMA, "name": hub_name, "description": desc[:100], "version": __version__,
    "repository": {"url": catalog.REPO_URL, "source": "github"}, "websiteUrl": catalog.REPO_URL,
    "packages": [
        {"registryType": "pypi", "identifier": "platform-mcp-hub", "version": __version__, "runtimeHint": "uvx", "transport": {"type": "stdio"},
         "packageArguments": [{"type": "positional", "value": "directory"}]},
        {"registryType": "npm", "identifier": "platform-mcp-hub", "version": __version__, "runtimeHint": "npx", "transport": {"type": "stdio"},
         "packageArguments": [{"type": "positional", "value": "directory"}]},
    ],
}, indent=1) + "\n", encoding="utf-8")
(hub / "manifest.json").write_text(json.dumps({
    "manifest_version": "0.2", "name": "platform-mcp-hub-directory", "display_name": "platform-mcp-hub directory", "version": __version__,
    "description": desc, "author": {"name": "platform-mcp contributors", "url": catalog.REPO_URL}, "license": "Apache-2.0",
    "server": {"type": "node", "entry_point": "platform-mcp-hub", "mcp_config": {"command": "npx", "args": ["-y", "platform-mcp-hub", "directory"]}},
    "tools": [{"name": "list_categories", "description": "Categories with counts and shared verbs."},
              {"name": "list_platforms", "description": "Browse or search platforms."},
              {"name": "describe_platform", "description": "Tools, credentials and run commands for one platform."},
              {"name": "search_capabilities", "description": "Platforms supporting a verb or capability."}],
}, indent=1) + "\n", encoding="utf-8")

# the PyPI page: usage, plus every registry name the package serves (the registry checks for `mcp-name: <name>`)
names = sorted({catalog.registry_name(e["id"], e["category"]) for _, e in served} | {hub_name})
banner = ("" if gen.published() else
          "> **Unpublished.** This is the README PyPI will show once platform-mcp-hub is published; until then, run it from source "
          f"(`uvx --from git+{catalog.REPO_URL} platform-mcp-hub ...`).\n\n")
(ROOT / "runtime" / "python" / "README.md").write_text(
    "# platform-mcp-hub\n\n" + banner +
    f"MCP servers for {len(served)} platform APIs from one evidence-only catalog: job boards, freelance marketplaces, ad networks, "
    "e-commerce channels and suppliers, messaging, social networks, sales data, trading venues, market data and automotive. "
    "Every tool maps to an endpoint documented on the platform's own pages.\n\n"
    "```bash\nuvx platform-mcp-hub list                  # every served platform\nuvx platform-mcp-hub describe reed           # tools, credentials (PLATFORM_MCP_REED_*), run commands\n"
    "uvx platform-mcp-hub serve reed              # stdio MCP server\nuvx platform-mcp-hub serve reed --http      # Streamable HTTP on 127.0.0.1:8000/mcp\n"
    "uvx platform-mcp-hub serve --entry my.json   # an entry you wrote yourself\nuvx platform-mcp-hub directory              # one server that searches the whole catalog\n```\n\n"
    "The same CLI ships on npm (`npx platform-mcp-hub serve reed`). Source, docs, limits and security policy: "
    f"{catalog.REPO_URL}\n\nLicence: Apache-2.0.\n\n"
    "<!-- MCP registry ownership: the registry accepts a server whose PyPI README names it.\n" + "".join(f"mcp-name: {n}\n" for n in names) + "-->\n",
    encoding="utf-8")

# catalog/index.json: counts per category (no upstream source tree needed)
index = {"categories": {}, "served_total": len(served)}
for p, e in catalog.iter_entries(root=ROOT / "catalog"):
    if p.name in ("index.json", "directory.json"):
        continue
    c = index["categories"].setdefault(e["category"], {"entries": 0, "has_api_yes": 0, "official_mcp": 0, "served": 0, "served_ids": []})
    c["entries"] += 1
    c["has_api_yes"] += int((e.get("discovery") or {}).get("has_api") == "yes")
    c["official_mcp"] += int(bool(e.get("official_mcp")))
    if isinstance(e.get("adapter"), dict):
        c["served"] += 1
        c["served_ids"].append(e["id"])
index["categories"] = dict(sorted(index["categories"].items()))
(ROOT / "catalog" / "index.json").write_text(json.dumps(index, indent=1) + "\n", encoding="utf-8")

build_directory.main()
