"""Compact the whole catalog into catalog/directory.json for the directory server (both languages).

The directory answers "which platforms exist, which have an API, which have a ready MCP server,
what can it do and how do I run it" without parsing 3,000+ full entries at start-up."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog"
os.environ["PLATFORM_MCP_HUB_CATALOG"] = str(CATALOG)
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub import catalog  # noqa: E402

TARGET = CATALOG / "directory.json"  # ships inside both packages with the rest of the catalog


def _env_names(pid: str, adapter: dict) -> list[dict]:
    out = []
    auth = adapter.get("auth") or {}
    for f in list(auth.get("fields") or []) + list(adapter.get("config_fields") or []):
        name = f["name"] if isinstance(f, dict) else str(f)
        out.append({"env": f"PLATFORM_MCP_{pid.upper()}_{name.upper()}", "required": bool(f.get("required", True)) if isinstance(f, dict) else True,
                    "help": (f.get("help") if isinstance(f, dict) else None)})
    envs = sorted(adapter.get("environments") or {})
    if envs:  # vendor environments (sandbox): PLATFORM_MCP_<ID>_ENV selects one
        out.append({"env": f"PLATFORM_MCP_{pid.upper()}_ENV", "required": False, "help": "Vendor environment: " + ", ".join(["production", *envs]) + " (default production)"})
    return out


def build() -> dict:
    platforms = []
    categories: dict[str, dict] = {}
    for p in sorted(CATALOG.glob("*/*.json")):
        if p.parent.name in ("schema", "sources"):
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        cat, pid = d["category"], d["id"]
        disc = d.get("discovery") or {}
        adapter = d.get("adapter")
        served = bool(adapter)
        official = []
        for m in d.get("official_mcp") or []:
            if isinstance(m, dict):
                official.append({k: m.get(k) for k in ("name", "url", "repo", "transport", "note") if m.get(k)})
            elif isinstance(m, str):
                official.append({"url": m})
        rec = {
            "id": pid, "category": cat, "label": d.get("label") or pid, "lane": d.get("lane"), "kind": d.get("kind"),
            "regions": d.get("regions"), "url": d.get("url"), "docs_url": d.get("docs_url"), "verified_at": d.get("verified_at"),
            "has_api": disc.get("has_api"), "auth": disc.get("auth"), "access": disc.get("access"),
            "capabilities": disc.get("capabilities") or [], "sdks": disc.get("sdks") or [], "kinds": disc.get("kinds") or [],
            "official_mcp": official, "forbids_automation": bool(d.get("forbids_automation")),
            "terms_note": (d.get("terms_note") or "")[:240] or None,
            "served": served,
            "tools": sorted(adapter["tools"]) if served else sorted({t["name"] for t in d.get("tools") or [] if isinstance(t, dict) and t.get("name")}),
        }
        if served:
            rec["not_offered"] = adapter.get("not_offered") or {}
            rec["credentials"] = _env_names(pid, adapter)
            rec["serve"] = catalog.serve_ref(pid, cat)
            rec["registry_name"] = catalog.registry_name(pid, cat)
            rec["base_url"] = adapter.get("base_url")
            rec["auth_type"] = (adapter.get("auth") or {}).get("type", "none")
            rec["version"] = d.get("version", "0.1.0")
        platforms.append(rec)
        c = categories.setdefault(cat, {"category": cat, "platforms": 0, "served": 0, "api_platforms": 0})
        c["platforms"] += 1
        c["served"] += int(served)
        c["api_platforms"] += int(disc.get("has_api") == "yes")
    vocab = json.loads((CATALOG / "schema" / "vocab.json").read_text(encoding="utf-8"))
    verbs = {cat: {verb: {"title": v.get("title"), "description": v.get("description"), "read_only": v.get("read_only", False)} for verb, v in cv.items()}
             for cat, cv in vocab.items() if isinstance(cv, dict)}
    try:
        release = json.loads((CATALOG / "schema" / "release.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        release = {}
    snapshot = {"platforms": len(platforms), "served": sum(c["served"] for c in categories.values()), "published": release.get("published") is True}
    return {"snapshot": snapshot, "platforms": platforms, "categories": sorted(categories.values(), key=lambda c: c["category"]), "verbs": verbs}


def main() -> int:
    data = build()
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    TARGET.write_text(text + "\n", encoding="utf-8")
    print(f"directory: {len(data['platforms'])} platforms, {sum(c['served'] for c in data['categories'])} served, {len(text)//1024} KiB -> {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
