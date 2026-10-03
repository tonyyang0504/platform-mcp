"""Credentials come from the environment for stdio servers (the MCP authorization spec says
stdio servers SHOULD take them from the environment); they are never logged or echoed."""

import os
import re

from .errors import AuthError

_SECRET_RE = re.compile(
    r"""(?i)(["']?)((?:api[_-]?key|access[_-]?token|refresh[_-]?token|id[_-]?token|client[_-]?secret|token|secret|password|authorization|bearer|jwt))\1(\s*[:=]\s*)((?:bearer|basic|token|bot|oauth|digest)\s+(?=[^\s"']))?("[^"]*"|'[^']*'|\S+)"""
)
_KNOWN: set[str] = set()


def register_secret(value: object) -> None:
    """Remember a credential or minted token so it is redacted wherever it appears, including
    platform error bodies that echo it back in JSON or prose, URL-encoded (a query string or form
    body echoed back) or form-encoded (spaces as '+')."""
    if isinstance(value, str) and len(value) >= 6:
        from urllib.parse import quote, quote_plus
        _KNOWN.update({value, quote(value, safe=""), quote(value), quote_plus(value, safe="")})


def env_name(platform_id: str, field: str) -> str:
    return f"PLATFORM_MCP_{platform_id.upper()}_{field.upper()}"


def resolve(platform_id: str, auth: dict, config_fields: list | None = None) -> dict[str, str]:
    """Return the credential fields the adapter asks for, plus non-secret per-install config
    fields (sender address, User-Agent contact, default country...). Missing required fields
    raise AuthError with the exact environment variable names to set."""
    out: dict[str, str] = {}
    missing = []
    for field in list(auth.get("fields", [])) + list(config_fields or []):
        name = field["name"] if isinstance(field, dict) else str(field)
        required = field.get("required", True) if isinstance(field, dict) else True
        value = os.environ.get(env_name(platform_id, name))
        if value:
            out[name] = value
        elif required:
            missing.append(env_name(platform_id, name))
    if missing:
        raise AuthError("missing credentials; set " + ", ".join(missing))
    return out


def scrub(text: str) -> str:
    out = text or ""
    for value in sorted(_KNOWN, key=len, reverse=True):
        if value in out:
            out = out.replace(value, "<redacted>")
    return _SECRET_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}{m.group(1)}{m.group(3)}{m.group(4) or ''}<redacted>", out)
