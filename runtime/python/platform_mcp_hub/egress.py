"""Before try_tool and live_verify call a served entry for real, every host its adapter would contact (as
PLATFORM_MCP_<ID>_ENV / _BASE_URL and a plan's config select it: base URL, absolute tool paths, token and
login URLs) must resolve to public addresses only. An entry may have been written from a hostile document
(the forge's workflow), and try_tool prints the raw response: pointed at an intranet host it would read it.
PLATFORM_MCP_ALLOW_PRIVATE_URLS=1 lifts the check (a local mock, a private gateway on purpose)."""
from __future__ import annotations

import re

from . import environment, netguard
from .errors import PlatformError

RESOLVER = None  # tests inject one; None = the system resolver


def entry_urls(entry: dict, environ: dict) -> list[tuple[str, str]]:
    """(where, url) for every URL the effective adapter calls; per-install {placeholders} are filled from environ."""
    pid = entry["id"]
    try:
        eff, _ = environment.select(pid, entry["adapter"], environ)
    except PlatformError:
        eff = entry["adapter"]  # a bad ENV/BASE_URL is reported by the server itself, before any request
    auth = eff.get("auth") or {}
    urls = [("base_url", eff.get("base_url"))]
    urls += [(f"tool {verb}", t.get("path")) for verb, t in (eff.get("tools") or {}).items() if isinstance(t, dict) and str(t.get("path", "")).startswith(("http://", "https://"))]
    if auth.get("token_url"):
        urls.append(("token_url", auth["token_url"]))
    login = auth.get("login")
    if isinstance(login, dict) and str(login.get("path", "")).startswith(("http://", "https://")):
        urls.append(("login", login["path"]))
    out = []
    for where, url in urls:
        if not isinstance(url, str) or not url:
            continue
        url = re.sub(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", lambda m: environ.get(f"PLATFORM_MCP_{pid.upper()}_{m.group(1).upper()}") or m.group(0), url)
        host_part = url.split("/", 3)[2] if url.count("/") >= 2 else ""
        if not host_part or "{" in host_part:
            continue  # a host that is still a placeholder: nothing to check until the operator configures it
        out.append((where, url))
    return out


async def blocked(entry: dict, environ: dict) -> list[str]:
    """Why the entry must not be called from this machine (empty when every host is public)."""
    problems = []
    for where, url in dict.fromkeys(entry_urls(entry, environ)):
        try:
            await netguard.check_url(url, RESOLVER, what=f"the entry's {where} host")  # never names the host (a BASE_URL override is a secret)
        except PlatformError as exc:
            problems.append(str(exc))
    return problems
