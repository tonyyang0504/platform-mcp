"""Vendor environments (sandbox, test) for one served entry. The TypeScript runtime's environment.ts
implements the same rules; both are exercised by tests/test_environments_python.py and
tests/environments.typescript.test.mjs with the same cases.

The catalog may declare ``adapter.environments {name: {...}}``; production is the adapter itself and is
never declared. The operator selects one with ``PLATFORM_MCP_<ID>_ENV=<name>`` (unset, empty or
``production`` = production) and may point the server at any other host with
``PLATFORM_MCP_<ID>_BASE_URL=https://…`` (a mock, a regional or private gateway). Both are read when the
first tool is called, so a bad value is an ``invalid_input`` tool error naming the variable, never a
crash; the override value itself is never echoed and is redacted from every later message.

An environment may set:
  base_url    replaces adapter.base_url
  token_url   replaces adapter.auth.token_url (OAuth2 grants and signed token requests)
  auth_url    the consent (authorize) URL a user opens once to obtain a refresh token (documentation
              for the operator and the auth audit; the runtime never opens it)
  scope       replaces adapter.auth.scope
  login_path  replaces adapter.auth.login.path (session logins)
  hosts       {production host: environment host}: rewrites absolute tool paths, an absolute login
              path and, unless token_url is given, the token URL (Microsoft Advertising calls two hosts)
  headers     merged over adapter.headers (Walmart's WM_SANDBOX: v2 selects the dynamic sandbox)
  same_host   true: the vendor tests on the production host (test accounts, test-mode keys); selecting
              the environment changes nothing but is accepted, and ``notes`` says what to use instead
  docs, verified_at, notes   the vendor page the values come from (required), when it was opened, and
              what differs (credentials, limits)
"""

import copy
import os
import re
from urllib.parse import urlsplit

from .credentials import env_name, register_secret
from .errors import InvalidInput

PRODUCTION = "production"
ENV_FIELD = "ENV"
BASE_URL_FIELD = "BASE_URL"
URL_KEYS = ("base_url", "token_url", "auth_url", "scope", "login_path", "hosts", "headers", "same_host")
META_KEYS = ("docs", "verified_at", "notes")
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
# https, a host name / IPv4 / bracketed IPv6, an optional port, an optional path; no user info, query or fragment
HTTPS_URL_RE = re.compile(r"^https://(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*|\[[0-9A-Fa-f:.]+\])(?::[0-9]{1,5})?(?:/[^\s?#]*)?$")


def valid_https_url(value: str) -> bool:
    return bool(HTTPS_URL_RE.match(value or ""))


def _host(url: str) -> str:
    try:
        return urlsplit(url).netloc
    except ValueError:
        return ""


def _rehost(url: str, hosts: dict) -> str:
    """Swap the host of an absolute URL when the environment maps it; other URLs are unchanged."""
    if not isinstance(url, str) or not url.startswith("https://") or not hosts:
        return url
    host = _host(url)
    if host in hosts:
        return "https://" + hosts[host] + url[len("https://") + len(host):]
    return url


def _why_invalid(value: str) -> str:
    """Which rule a rejected override broke, without repeating the value (it may name a private host)."""
    low = value.strip().lower()
    if not low.startswith("https://"):
        return "it must start with https://"
    rest = value.strip()[len("https://"):]
    if "@" in rest.split("/", 1)[0]:
        return "it must not carry user info (credentials) before the host"
    if "?" in rest or "#" in rest:
        return "it must not carry a query string or fragment"
    return "it must be https://host[:port][/path] with a valid host name"


def select(platform_id: str, adapter: dict, environ: dict | None = None) -> tuple[dict, str]:
    """Return ``(effective adapter, environment name)`` for this process. The effective adapter is a
    copy; the catalog spec is never mutated. ``environment name`` is ``production`` or a declared
    environment, suffixed with ``+base_url`` when the operator override is in effect."""
    env = os.environ if environ is None else environ
    var = env_name(platform_id, ENV_FIELD)
    raw = (env.get(var) or "").strip()
    name = raw.lower() or PRODUCTION
    declared = adapter.get("environments") or {}
    out = copy.deepcopy({k: v for k, v in adapter.items() if k != "environments"})
    if name != PRODUCTION:
        if not NAME_RE.match(name):
            raise InvalidInput(f"configuration: {var} must be an environment name ({', '.join([PRODUCTION, *sorted(declared)])})")
        if name not in declared:
            available = ", ".join([PRODUCTION, *sorted(declared)])
            raise InvalidInput(f"configuration: {var}={name} is not an environment of this server; available: {available}")
        spec = declared[name]
        auth = out.setdefault("auth", {"type": "none"})
        hosts = spec.get("hosts") or {}
        if hosts:
            for tool in (out.get("tools") or {}).values():
                if isinstance(tool.get("path"), str):
                    tool["path"] = _rehost(tool["path"], hosts)
            login = auth.get("login")
            if isinstance(login, dict) and isinstance(login.get("path"), str):
                login["path"] = _rehost(login["path"], hosts)
            if auth.get("token_url"):
                auth["token_url"] = _rehost(auth["token_url"], hosts)
            out["base_url"] = _rehost(out["base_url"], hosts)
        if spec.get("base_url"):
            out["base_url"] = spec["base_url"]
        if spec.get("token_url"):
            auth["token_url"] = spec["token_url"]
        if spec.get("scope"):
            auth["scope"] = spec["scope"]
        if spec.get("login_path") and isinstance(auth.get("login"), dict):
            auth["login"]["path"] = spec["login_path"]
        if spec.get("auth_url"):
            auth["auth_url"] = spec["auth_url"]
        if spec.get("headers"):
            out["headers"] = {**(out.get("headers") or {}), **spec["headers"]}
    override_var = env_name(platform_id, BASE_URL_FIELD)
    override = (env.get(override_var) or "").strip()
    if override:
        if len(re.sub(r"^[A-Za-z][A-Za-z0-9+.-]*://", "", override)) >= 6:
            register_secret(override)  # an operator's private gateway never appears in a message (a bare scheme is not a secret)
        if not valid_https_url(override):
            raise InvalidInput(f"configuration: {override_var} is not a valid override: {_why_invalid(override)}")
        out["base_url"] = override
        name = f"{name}+base_url"
    return out, name


def state_key(platform_id: str, environment: str) -> str:
    """Rotated refresh tokens are saved per environment: a sandbox token must never replace a production one."""
    base = environment.split("+", 1)[0]
    return platform_id if base == PRODUCTION else f"{platform_id}.{base}"


def lint(adapter: dict) -> list[str]:
    """Errors in ``adapter.environments`` (platform-mcp-hub lint calls this so the rules live beside the code)."""
    errs = []
    names = {str(f.get("name", "")).lower() for f in list((adapter.get("auth") or {}).get("fields") or []) + list(adapter.get("config_fields") or []) if isinstance(f, dict)}
    for clash in sorted(names & {ENV_FIELD.lower(), BASE_URL_FIELD.lower()}):
        errs.append(f"a credential/config field named {clash!r} collides with PLATFORM_MCP_<ID>_{clash.upper()} (environment selection)")
    envs = adapter.get("environments")
    if envs is None:
        return errs
    if not isinstance(envs, dict) or not envs:
        return errs + ["adapter.environments must be a non-empty object {name: {...}}"]
    prod_hosts = {_host(adapter.get("base_url", ""))}
    prod_hosts |= {_host(t.get("path", "")) for t in (adapter.get("tools") or {}).values() if isinstance(t, dict) and str(t.get("path", "")).startswith("https://")}
    tok = (adapter.get("auth") or {}).get("token_url")
    if tok:
        prod_hosts.add(_host(tok))
    for name, spec in envs.items():
        where = f"adapter.environments.{name}"
        if not NAME_RE.match(str(name)) or name == PRODUCTION:
            errs.append(f"{where}: the name must match [a-z][a-z0-9_]* and cannot be 'production' (production is the adapter itself)")
        if not isinstance(spec, dict):
            errs.append(f"{where} must be an object")
            continue
        unknown = set(spec) - set(URL_KEYS) - set(META_KEYS)
        if unknown:
            errs.append(f"{where}: unknown keys {sorted(unknown)} (allowed: {', '.join(URL_KEYS + META_KEYS)})")
        if not isinstance(spec.get("docs"), str) or not spec["docs"].startswith("https://"):
            errs.append(f"{where}.docs must cite the vendor page (https URL) the values come from")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(spec.get("verified_at", ""))):
            errs.append(f"{where}.verified_at must be YYYY-MM-DD")
        if not isinstance(spec.get("notes"), str) or not spec["notes"].strip():
            errs.append(f"{where}.notes must say what differs from production (credentials, limits)")
        same = spec.get("same_host")
        changes = [k for k in ("base_url", "token_url", "login_path", "hosts", "headers", "scope") if k in spec]
        if same is not None and same is not True:
            errs.append(f"{where}.same_host must be true when present")
        if same is True and changes:
            errs.append(f"{where}: same_host cannot be combined with {changes}")
        if same is not True and not changes:
            errs.append(f"{where}: set base_url/token_url/hosts/headers, or same_host: true when the vendor tests on the production host")
        for k in ("base_url", "token_url", "auth_url"):
            if k in spec:
                v = spec[k]
                if not isinstance(v, str) or not valid_https_url(re.sub(r"\{[A-Za-z0-9_]+\}", "x", v)):
                    errs.append(f"{where}.{k} must be an https URL without user info, query or fragment")
        if "token_url" in spec and not tok:
            errs.append(f"{where}.token_url is set but the adapter's auth has no token_url")
        if "base_url" in spec and spec.get("base_url") == adapter.get("base_url"):
            errs.append(f"{where}.base_url equals the production base_url (use same_host: true)")
        if "login_path" in spec and not isinstance((adapter.get("auth") or {}).get("login"), dict):
            errs.append(f"{where}.login_path is set but the adapter has no session login")
        if "scope" in spec and not isinstance(spec["scope"], str):
            errs.append(f"{where}.scope must be a string")
        hosts = spec.get("hosts")
        if hosts is not None:
            if not isinstance(hosts, dict) or not hosts:
                errs.append(f"{where}.hosts must be a non-empty object {{production host: environment host}}")
            else:
                for src, dst in hosts.items():
                    if src not in prod_hosts:
                        errs.append(f"{where}.hosts: {src!r} is not a host the production adapter calls")
                    if not isinstance(dst, str) or not valid_https_url("https://" + dst) or "/" in dst:
                        errs.append(f"{where}.hosts: {src!r} must map to a bare host name")
        headers = spec.get("headers")
        if headers is not None and (not isinstance(headers, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in headers.items())):
            errs.append(f"{where}.headers must map header names to string values")
    return errs
