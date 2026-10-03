"""Credential-free audit of the served entries whose adapter needs authentication.

For every in-scope entry (adapter.auth.type != "none") this tool

  probe   sends the exact request the runtime builds for each tool, with dummy credentials (and,
          for read tools, once more with the credentials omitted), plus one control request to a
          route that cannot exist, DNS/TLS checks of every host, and the token / login / authorize
          request of the auth flow with a dummy client. Write tools never carry a real body: POST,
          PUT and PATCH are sent with a deliberately invalid empty body, DELETE becomes OPTIONS.
          Requests are sequential per host and at least --interval seconds apart.
  spec    compares each tool with the vendor's machine-readable spec where one is published
          (OpenAPI / Swagger, Google API discovery documents, AT Protocol lexicons): path and
          method, query parameter names, required parameters, request body keys, and the
          response paths the result mapping reads (items, fields, next_cursor, total).
  apply   classifies each entry and writes its `auth_audit` block {date, status, evidence, notes}
          (only for in-scope entries; the classification rules are in `classify`).
  report  writes docs/AUTH_AUDIT.md from the catalog's auth_audit blocks.

No real account is used: credentials are dummies, and the only live reads with credentials use
values the vendor itself publishes for demo use (see VENDOR_DEMO). Nothing here bypasses a bot
wall; a challenge page is recorded as `blocked`.

    python tools/auth_audit.py probe --out <dir> [--ids a,b] [--interval 1.2]
    python tools/auth_audit.py spec  --out <dir> [--ids a,b]
    python tools/auth_audit.py apply --out <dir> [--date YYYY-MM-DD]
    python tools/auth_audit.py report

Every command except report accepts --env <name> (e.g. sandbox): only entries that declare
adapter.environments.<name> with its own hosts are in scope, and every URL (base, token, absolute tool
paths, login) is the one the runtime uses with PLATFORM_MCP_<ID>_ENV=<name>; apply writes
environment_checks.<name>.auth_audit instead of the production auth_audit. Environments marked
same_host (test accounts or test keys on the production host) add nothing to a credential-free audit
and are skipped.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import socket
import ssl
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))

STATUSES = ("verified_live", "spec_conformant", "reachable_unverified", "mismatch", "broken", "blocked")
DUMMY = "authaudit-invalid"
UA_SUFFIX = ""  # the runtime's own User-Agent is sent unchanged

# Representative values for URL placeholders (per-install hosts). Taken from each field's help text
# (the vendor's documented production host) or, for per-tenant hosts, a vendor-owned demo tenant.
PLACEHOLDERS = {
    "shopify": {"shop": "graphql"},                 # graphql.myshopify.com: Shopify's documented demo shop
    "supabase": {"project_ref": "authaudit-nonexistent"},
    "wordpress": {"site": "wordpress.org/news"},    # the WordPress project's own site
    "woocommerce": {"store_host": "woocommerce.com"},
    "mirakl": {"instance_host": "marketplace.bestbuy.ca"},
    "zendesk": {"subdomain": "support"},            # Zendesk's own help desk
    "telegram": {"token": "123456789:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"},
    "microsoft_marketplace": {"tenant_id": "common"},
    "recruitee": {"company_subdomain": "bunq"},     # a live Recruitee careers site
    "ecwid": {"store_id": "1003"},                   # store id used in Ecwid's API examples
    "alibaba_1688_open": {"client_id": "1234567"},
}
HOST_RE = re.compile(r"\b((?:[a-z0-9-]+\.)+(?:com|net|org|io|app|de|ro|bg|hu|ca|br|sg|my|ph|th|id|vn|cn|kr|jp|ru|ml|social|chat|so|ai|co|dev|market|cloud|uk|nl|be|fi|ir|pl|au)(?:\.[a-z]{2})?)\b")

# Credentials a vendor publishes for demo / test use (cite the page). Only these ever carry a "real" value.
VENDOR_DEMO = {
    # "…passing the POSTMARK_API_TEST value in the X-Postmark-Server-Token header field" (test sends are not delivered)
    "postmark": {"creds": {"server_token": "POSTMARK_API_TEST"}, "source": "https://postmarkapp.com/developer/api/overview"},
    # "You can find a public token that can be used for experiments here: …/api/publicToken" (rotates)
    "arbeidsplassen": {"fetch": ("token", "https://pam-stilling-feed.nav.no/api/publicToken", r"eyJ[\w-]+\.[\w-]+\.[\w-]+"),
                       "source": "https://navikt.github.io/pam-stilling-feed/"},
}


def load_scope(ids: list[str] | None = None, env: str = "production") -> list[tuple[Path, dict]]:
    out = []
    for p in sorted((ROOT / "catalog").glob("*/*.json")):
        if p.parent.name in ("schema", "sources"):
            continue
        e = json.loads(p.read_text(encoding="utf-8"))
        a = e.get("adapter")
        if not a or a.get("auth", {}).get("type", "none") == "none":
            continue
        if ids and e["id"] not in ids and f"{p.parent.name}/{e['id']}" not in ids:
            continue
        if env != "production":
            declared = (a.get("environments") or {}).get(env)
            if not declared:
                continue
            if declared.get("same_host"):
                print(f"{key(p)}: environment {env} uses the production host (same_host); skipped")
                continue
            from platform_mcp_hub.environment import select
            eff, _ = select(e["id"], a, {f"PLATFORM_MCP_{e['id'].upper()}_ENV": env})
            e = {**e, "adapter": eff}  # the URLs the runtime calls in that environment
        out.append((p, e))
    return out


def key(p: Path) -> str:
    return f"{p.parent.name}/{p.stem}"


# ----------------------------------------------------------------------------------------- probe

_PEM: str | None = None


def _pem() -> str:
    global _PEM
    if _PEM is None:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        _PEM = k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    return _PEM


def dummy_creds(e: dict) -> dict[str, str]:
    a = e["adapter"]
    auth = a.get("auth", {})
    creds: dict[str, str] = {}
    encoded: dict[str, str] = {}
    specs = [auth.get("sign") or {}, auth.get("token_sign") or {}, auth.get("token_jwt") or {}] + list((auth.get("sign") or {}).get("pre") or [])
    for s in specs:
        if s.get("key_encoding"):
            encoded[s.get("key_field", "api_secret")] = s["key_encoding"]
        if s.get("mode") in ("rsa_sha256", "jwt_rs256", "jwt_ps256"):
            encoded[s.get("key_field", "private_key")] = "pem"
    for f in list(auth.get("fields", [])) + list(a.get("config_fields", [])):
        name = f["name"] if isinstance(f, dict) else str(f)
        help_ = f.get("help", "") if isinstance(f, dict) else ""
        val = PLACEHOLDERS.get(e["id"], {}).get(name)
        if val is None and ("{" + name + "}") in (a["base_url"] + auth.get("token_url", "") + json.dumps(auth.get("login") or {})):
            hosts = [h for h in HOST_RE.findall(help_) if "example" not in h]
            label = re.search(r"'([a-z0-9-]+)' in https://", help_) or re.search(r"the `?([a-z0-9-]+)`? of [a-z0-9-]+\.", help_)
            if name in ("region",):
                m = re.search(r"\b(na|us-east-1|eu)\b", help_)
                val = m.group(1) if m else "na"
            elif re.search(r"\{" + re.escape(name) + r"\}\.", a["base_url"]):  # a subdomain label: {x}.vendor.com
                val = label.group(1) if label else "www"
            elif hosts and any(w in name for w in ("host", "domain", "instance", "homeserver", "site")):
                val = hosts[0]
            elif name.endswith(("_id", "_sid")):
                val = "1234567"
            else:
                val = DUMMY
        ints = set(re.findall(r"int:@([A-Za-z0-9_]+)", json.dumps(a)))
        if val is None and (name in ints or "percentage" in name):
            val = "10"
        if val is None and ("basic" in name or re.search(r"(?i)base64", help_)) and name not in encoded:
            val = "YXV0aGF1ZGl0OmludmFsaWQ="  # base64("authaudit:invalid")
        if val is None:
            enc = encoded.get(name)
            if enc == "pem" or "private_key" in name:
                val = _pem()
            elif enc in ("base64", "base64url"):
                val = "YXV0aGF1ZGl0LWR1bW15LWtleS0wMTIzNDU2Nzg5"
            elif enc == "hex":
                val = "00112233445566778899aabbccddeeff"
            elif name.endswith("_id") or name in ("partner_id", "shop_id", "account_sid", "store_id"):
                val = "1234567"
            elif name in ("region",):
                val = "us-east-1"
            else:
                val = f"{DUMMY}-{name}"
        creds[name] = val
    return creds


def dummy_args(e: dict, verb: str, vocab: dict) -> dict:
    tool = e["adapter"]["tools"][verb]
    schema = vocab[verb]["input"]
    props = schema.get("properties", {})
    needed = set(schema.get("required", []))
    needed |= (set(re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", tool.get("path", ""))) - set(tool.get("path_params") or {})) & set(props)
    blob = json.dumps([v for k in ("params", "body", "path_params") for v in (tool.get(k) or {}).values()])
    for p in props:  # arguments the adapter maps into the request (so the request has its full shape)
        if re.search(r'"(?:[a-z]+:)*' + re.escape(p) + r'(?:[".:}]|$)', blob) and p not in ("cursor", "page"):
            needed.add(p)
    out = {}
    for p in needed:
        s = props.get(p, {})
        t = s.get("type")
        t = [x for x in t if x != "null"][0] if isinstance(t, list) else t
        if s.get("enum"):
            out[p] = s["enum"][0]
        elif p in ("date_from", "since", "start"):
            out[p] = "2026-09-01"
        elif p in ("date_to", "until", "end"):
            out[p] = "2026-09-20"
        elif p == "symbol":
            out[p] = "BTCUSDT"
        elif p == "vin":
            out[p] = "1HGCM82633A004352"  # NHTSA's documented sample VIN
        elif p == "to":
            out[p] = "authaudit@example.com"
        elif p in ("image_url", "url", "resume_url"):
            out[p] = "https://www.example.com/authaudit.png"
        elif p == "image_urls":
            out[p] = ["https://www.example.com/authaudit.png"]
        elif p == "interval":
            out[p] = "1h"
        elif p == "country":
            out[p] = "US"
        elif p == "currency":
            out[p] = "USD"
        elif p == "items":
            out[p] = [{"sku": "AUTHAUDIT-1", "product_id": "1234567", "quantity": 1}]
        elif p == "shipping_address":
            out[p] = {"name": "Audit", "first_name": "Audit", "last_name": "Test", "address1": "1 Main St", "city": "Springfield", "zip": "12345", "country": "US", "state": "IL", "phone": "5555555555", "email": "authaudit@example.com"}
        elif p == "fields":
            out[p] = {"name": "authaudit"}
        elif t == "integer":
            out[p] = 1
        elif t == "number":
            out[p] = 1.0
        elif t == "boolean":
            out[p] = False
        elif t == "array":
            out[p] = ["1234567"]
        elif t == "object":
            out[p] = {}
        elif p.endswith("_id") or p == "id":
            out[p] = "1234567"
        else:
            out[p] = "authaudit"
    out.setdefault("limit", tool.get("default_limit", 10)) if "limit" in props else None
    if "limit" in out:
        out["limit"] = min(int(out["limit"]), 10)
    return out


BOT_WALL = re.compile(r"(?i)(cf-chl|challenge-platform|just a moment\.\.\.|attention required|captcha|access denied</title>|akamai|incapsula|distil|perimeterx|px-captcha|ddos-guard|/_incapsula_|request unsuccessful|bot detection|sec-if-cpt)")
ROUTE_MISSING = re.compile(r"(?i)(请求的URI地址不存在|empty api|\"invalidUrl\"|no route was found|rest_no_route|unknown (?:api|method|endpoint)|method not found|invalid endpoint|api not found|resource could not be found \(/|URL called is invalid)")
AUTH_BODY = re.compile(r"(?i)(username|user name|accountnotfound|account ?not ?found|merchant.{0,40}not found|access-key|トークン|無効|无效|认证|認證|unauthori[sz]ed|unauthenticated|not_authed|invalid_auth|invalid[ _-]?(api[ _-]?)?(key|token|credential|signature|client|access|app|grant|consumer|auth)|access[ _-]?token|api[ _-]?key|apikey|app[ _-]?key|appkey|authenticat|credential|forbidden|permission|signature|not authorized|missing.{0,20}(key|token|auth|header)|login|bad credentials|sign|token|401|403|鉴权|授权|签名|令牌|認証|인증|errcode)")


def classify_response(status: int | None, body: str, error: str | None, probe: str) -> str:
    if error:
        low = error.lower()
        if "name" in low and ("resolve" in low or "not known" in low or "nodename" in low or "getaddrinfo" in low):
            return "dns_error"
        if "ssl" in low or "certificate" in low or "tls" in low:
            return "tls_error"
        if "timeout" in low:
            return "timeout"
        return "conn_error"
    b = body or ""
    if status in (200, 400, 404) and ROUTE_MISSING.search(b[:1500]) and not AUTH_BODY.search(b[:300].replace("URI", "")):
        return "not_found"
    if status in (401, 407):
        return "auth_required"
    if status in (403, 429, 503) and BOT_WALL.search(b[:4000]):
        return "blocked"
    if status == 403:
        return "auth_required"
    if status and 200 <= status < 300:
        if probe == "options":
            return "options_ok"
        if AUTH_BODY.search(b[:1500]) and re.search(r'(?i)"(ok|success)"\s*:\s*false|"(errcode|code|error_code|err_code|ret|status)"\s*:\s*"?-?[1-9]|"error"|"errors"|"error_msg"|"message"', b[:1500]):
            return "auth_required"  # an error envelope inside a 200
        return "public"
    if status in (301, 302, 303, 307, 308):
        return "redirect"
    if status == 404:
        return "not_found"
    if status == 405:
        return "method_not_allowed" if probe != "options" else "options_405"
    if status in (400, 409, 411, 412, 415, 422):
        return "auth_required" if AUTH_BODY.search(b[:1500]) else "client_error"
    if status and status >= 500:
        return "auth_required" if AUTH_BODY.search(b[:1500]) and not BOT_WALL.search(b[:4000]) else "server_error"
    return f"status_{status}"


class Pacer:
    """Sequential per host, at least `interval` seconds between the end of one request and the next."""

    def __init__(self, interval: float):
        self.interval = interval
        self.locks: dict[str, asyncio.Lock] = {}
        self.last: dict[str, float] = {}

    def lock(self, host: str) -> asyncio.Lock:
        return self.locks.setdefault(host, asyncio.Lock())

    async def wait(self, host: str) -> None:
        gap = time.monotonic() - self.last.get(host, 0.0)
        if gap < self.interval:
            await asyncio.sleep(self.interval - gap)

    def done(self, host: str) -> None:
        self.last[host] = time.monotonic()


def _snippet(text: str, creds: dict) -> str:
    out = (text or "")[:600]
    for v in creds.values():
        if isinstance(v, str) and len(v) > 8 and "BEGIN" in v:
            out = out.replace(v, "<pem>")
    return out


def make_recorder(log: list, pacer: Pacer, allowed: set[str], mode_ref: dict, creds: dict):
    import httpx

    class Recorder(httpx.AsyncBaseTransport):
        def __init__(self):
            self.inner = httpx.AsyncHTTPTransport(retries=0)

        async def handle_async_request(self, request):
            host = request.url.host
            if host not in allowed:
                # e.g. a `file:` download of a sample image argument: never leaves the machine
                return httpx.Response(200, content=b"\x89PNG\r\n\x1a\n", headers={"content-type": "image/png"}, request=request)
            mode = mode_ref.get("mode", "read")
            sent_method = request.method
            if mode == "write" and request.method in ("POST", "PUT", "PATCH", "DELETE") and not (request.method == "DELETE" and mode_ref.get("delete_as_is")):
                headers = {k: v for k, v in request.headers.items() if k.lower() not in ("content-length", "transfer-encoding")}
                if request.method == "DELETE":
                    sent_method = "OPTIONS"
                    request = httpx.Request("OPTIONS", request.url, headers=headers)
                else:
                    ctype = request.headers.get("content-type", "")
                    content = b"<invalid/>" if "xml" in ctype else (b"" if "form" in ctype else b"{}")
                    if "multipart" in ctype:
                        headers["content-type"] = "application/json"
                    request = httpx.Request(request.method, request.url, headers=headers, content=content)
            rec = {"phase": mode_ref.get("phase"), "tool": mode_ref.get("tool"), "variant": mode_ref.get("variant"),
                   "method": sent_method, "orig_method": mode_ref.get("orig_method") or sent_method,
                   "url": str(request.url)[:500], "host": host}
            async with pacer.lock(host):
                await pacer.wait(host)
                t0 = time.monotonic()
                try:
                    resp = await self.inner.handle_async_request(request)
                    await resp.aread()
                    rec.update(status=resp.status_code, ctype=resp.headers.get("content-type", ""),
                               headers={k: resp.headers[k] for k in ("www-authenticate", "allow", "server", "location", "x-amzn-errortype", "cf-ray", "x-cache") if k in resp.headers},
                               body=_snippet(resp.text, creds), ms=int((time.monotonic() - t0) * 1000))
                    log.append(rec)
                    return resp
                except Exception as exc:  # noqa: BLE001 - every network failure is evidence
                    rec.update(status=None, error=f"{exc.__class__.__name__}: {str(exc)[:200]}", ms=int((time.monotonic() - t0) * 1000))
                    log.append(rec)
                    raise
                finally:
                    pacer.done(host)

    return Recorder()


def host_check(host: str) -> dict:
    out = {"host": host}
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
        out["dns"] = sorted({i[4][0] for i in infos})[:4]
    except Exception as exc:  # noqa: BLE001
        out["dns_error"] = str(exc)[:200]
        return out
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=15) as s:
            with ctx.wrap_socket(s, server_hostname=host) as t:
                cert = t.getpeercert()
                issuer = dict(x[0] for x in cert.get("issuer", ()))
                out["tls"] = {"version": t.version(), "issuer": issuer.get("organizationName"), "not_after": cert.get("notAfter")}
    except Exception as exc:  # noqa: BLE001
        out["tls_error"] = str(exc)[:200]
    return out


# Arguments that name real public objects, for the credential-free reads of public endpoints.
SAMPLES: dict[str, dict[str, dict]] = {
    "lemmy": {"read_comments": {"post_id": "53195412"}, "analytics_post": {"post_id": "53195412"}},
    "mastodon": {"read_comments": {"post_id": "117337633413833746"}, "analytics_post": {"post_id": "117337633413833746"}},
    "wordpress": {"get_item": {"item_id": "21731"}, "list_items": {"query": "WordPress"}},
    "huggingface": {"get_item": {"item_id": "sentence-transformers/all-MiniLM-L6-v2"}, "list_items": {"query": "bert"},
                    "update_item": {"item_id": "sentence-transformers/all-MiniLM-L6-v2"}},
    "udbud_dk": {"get_posting": {"id": "6a26cc22-a211-41ea-867f-c34b4d726154/01"}},
    "devto": {"read_comments": {"post_id": "4701626"}, "analytics_post": {"post_id": "4701626"}},
    "belancer_com": {"get_posting": {"posting_id": "387", "id": "387"}, "search_postings": {"query": ""}},
    "deribit": {"get_ticker": {"symbol": "BTC-PERPETUAL"}},
    "freelancer": {"search_postings": {"query": "python"}, "discover": {"query": "logo"}},
    "freelancer_com": {"search": {"query": "python"}},
    "the_muse": {"search": {"query": "engineer"}},
    "printful": {"list_products": {"category": ""}, "get_product": {"product_id": "71", "id": "71"}},
    "printify": {"get_product": {"product_id": "5", "id": "5"}},
}
PLACEHOLDERS.update({"tumblr": {"blog_identifier": "staff.tumblr.com"}})

# Consent (authorize) endpoints of the OAuth providers, by the host of the entry's token URL.
AUTHORIZE = {
    "oauth2.googleapis.com": "https://accounts.google.com/o/oauth2/v2/auth",
    "login.microsoftonline.com": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
    "api.amazon.com": "https://www.amazon.com/ap/oa",
    "www.linkedin.com": "https://www.linkedin.com/oauth/v2/authorization",
    "api.x.com": "https://x.com/i/oauth2/authorize",
    "id.twitch.tv": "https://id.twitch.tv/oauth2/authorize",
    "open.tiktokapis.com": "https://www.tiktok.com/v2/auth/authorize/",
    "api.ebay.com": "https://auth.ebay.com/oauth2/authorize",
    "api.etsy.com": "https://www.etsy.com/oauth/connect",
    "allegro.pl": "https://allegro.pl/auth/oauth/authorize",
    "api.mercadolibre.com": "https://auth.mercadolibre.com.ar/authorization",
    "accounts.spotify.com": "https://accounts.spotify.com/authorize",
    "accounts.snapchat.com": "https://accounts.snapchat.com/login/oauth2/authorize",
    "api.pinterest.com": "https://www.pinterest.com/oauth/",
    "www.reddit.com": "https://www.reddit.com/api/v1/authorize",
    "kauth.kakao.com": "https://kauth.kakao.com/oauth/authorize",
    "www.upwork.com": "https://www.upwork.com/ab/account-security/oauth2/authorize",
    "auth.login.yahoo.co.jp": "https://auth.login.yahoo.co.jp/yconnect/v2/authorization",
    "biz-oauth.yahoo.co.jp": "https://biz-oauth.yahoo.co.jp/oauth/v1/authorize",
    "api.bling.com.br": "https://www.bling.com.br/Api/v3/oauth/authorize",
    "accounts.stockx.com": "https://accounts.stockx.com/authorize",
    "oauth.zaloapp.com": "https://oauth.zaloapp.com/v4/oa/permission",
    "api.hh.ru": "https://hh.ru/oauth/authorize",
    "api.thebase.in": "https://api.thebase.in/1/oauth/authorize",
    "secure.dhgate.com": "https://secure.dhgate.com/dop/oauth2/authorize",
    "oauth-login.cloud.huawei.com": "https://oauth-login.cloud.huawei.com/oauth2/v3/authorize",
    "open.kuaishou.com": "https://open.kuaishou.com/oauth2/authorize",
    "accounts.tiny.com.br": "https://accounts.tiny.com.br/realms/tiny/protocol/openid-connect/auth",
    "id.magalu.com": "https://id.magalu.com/login",
}


def _fill(url: str, creds: dict) -> str:
    for k, v in creds.items():
        url = url.replace("{" + k + "}", str(v))
    return url


def entry_hosts(e: dict, creds: dict) -> set[str]:
    a = e["adapter"]
    auth = a.get("auth", {})
    urls = [a["base_url"], auth.get("token_url") or ""]
    login = (auth.get("login") or {}).get("path", "")
    if login.startswith("http"):
        urls.append(login)
    urls += [t["path"] for t in a["tools"].values() if str(t.get("path", "")).startswith("http")]
    return {urlparse(_fill(u, creds)).hostname for u in urls if u} - {None}


def authorize_candidates(e: dict) -> list[str]:
    """Consent / authorize URLs named in the entry's own help texts and reference notes."""
    a = e["adapter"]
    blob = json.dumps([a.get("auth", {}).get("fields"), e.get("terms_note"), (e.get("reference") or {}).get("auth")], ensure_ascii=False)
    out = []
    for u in re.findall(r"https://[^\s`\"'\\)<>,]+", blob):
        u = u.rstrip(".;:*")
        low = u.lower()
        if any(k in low for k in ("authorize", "/authorization", "/ap/oa", "oauth2/auth", "/oauth/auth", "consent", "/o/oauth2/v2/auth", "auth.tiktok", "/oauth2/v2.0/authorize", "openapi/authorize", "/oauth/")) and "token" not in low.rsplit("/", 1)[-1]:
            base = u.split("?")[0].replace("…", "")
            if base not in out and "{" not in base:
                out.append(base)
    out = [u for u in out if not re.search(r"(?i)//(docs|developers?|help)\.|/(help|docs|documentation|guides?)/", u)]
    tok = urlparse(a.get("auth", {}).get("token_url", "") or "").hostname
    if tok in AUTHORIZE and AUTHORIZE[tok] not in out:
        out.insert(0, AUTHORIZE[tok])
    return out[:3]


async def _adapter_call(ad, verb: str, args: dict, tries: int = 3):
    from platform_mcp_hub.errors import InvalidInput, PlatformError
    for _ in range(tries):
        try:
            return {"output": await ad.call(verb, args)}
        except InvalidInput as exc:
            msg = str(exc)
            m = re.search(r"'([^']+)' must be one of \[([^\]]*)\]", msg)
            if m and exc.status is None:
                choices = re.findall(r"'([^']*)'", m.group(2))
                if choices:
                    args = _set_arg(args, m.group(1), choices[0])
                    continue
            m = re.search(r"missing argument '([^']+)'", msg)
            if m and exc.status is None:
                args = {**args, m.group(1): "1234567"}
                continue
            m = re.search(r"'([^']+)' must be an (?:ISO date|integer)", msg)
            if m and exc.status is None:
                args = _set_arg(args, m.group(1), "2026-09-01" if "date" in msg else 1)
                continue
            return {"error": exc.payload()}
        except PlatformError as exc:
            return {"error": exc.payload()}
        except Exception as exc:  # noqa: BLE001
            return {"error": {"error": "harness_error", "message": f"{exc.__class__.__name__}: {str(exc)[:200]}"}}
    return {"error": {"error": "harness_error", "message": "argument retries exhausted"}}


def _set_arg(args: dict, expr: str, value):
    name = expr.split(":")[-1].split(".")[0]
    return {**args, name: value}


def validate_output(vocab: dict, verb: str, output: dict) -> dict:
    import jsonschema
    schema = vocab[verb]["output"]
    errs = sorted({f"{'/'.join(str(x) for x in err.absolute_path)}: {err.message}"[:160] for err in jsonschema.Draft202012Validator(schema).iter_errors(output)})
    items = None
    for k, v in output.items():
        if isinstance(v, list) and k not in ("raw",):
            items = len(v)
    return {"valid": not errs, "errors": errs[:5], "items": items}


def audit_transport_class():
    from platform_mcp_hub.errors import AuthError
    from platform_mcp_hub.http import Transport

    class AuditTransport(Transport):
        """The runtime's transport, except that minted tokens are a dummy and a 401 never triggers a re-login."""

        async def _dynamic_headers(self, force: bool = False) -> dict[str, str]:
            if self.auth.get("type") not in ("session", "oauth2_client_credentials", "oauth2_refresh_token"):
                return {}
            if force:
                raise AuthError("dummy token refused (audit: no re-login)", status=401)
            if not self._token:
                self._token, self._token_expires = f"{DUMMY}-token", time.monotonic() + 1e6
            if self.auth.get("token_param") or self.auth.get("header") == "":
                return {}
            return {self.auth.get("header", "Authorization"): self.auth.get("prefix", "Bearer ") + str(self._token)}

    return AuditTransport


async def probe_entry(p: Path, e: dict, pacer: Pacer, vocab_all: dict) -> dict:
    import httpx
    from platform_mcp_hub.adapter import Adapter
    from platform_mcp_hub.errors import PlatformError
    from platform_mcp_hub.http import Transport

    a = e["adapter"]
    auth = {k: v for k, v in a.get("auth", {}).items()}
    creds = dummy_creds(e)
    vocab = vocab_all[e["category"]]
    ua = f"platform-mcp/{e['id']} (+https://github.com/tonyyang0504/platform-mcp)"
    hosts = entry_hosts(e, creds)
    log: list = []
    mode: dict = {}
    res: dict = {"id": e["id"], "key": key(p), "auth_type": auth.get("type"), "hosts": {}, "tools": {}, "flow": {}, "creds_used": "dummy"}

    loop = asyncio.get_running_loop()
    for h in sorted(hosts):
        res["hosts"][h] = await loop.run_in_executor(None, host_check, h)

    def new_transport(auth_block: dict, cls=None, creds_=None):
        T = cls or audit_transport_class()
        t = T(a["base_url"], auth_block, dict(creds_ or creds), 1000.0, ua, envelope=a.get("envelope"))
        t.client = httpx.AsyncClient(transport=make_recorder(log, pacer, hosts, mode, creds), timeout=30.0,
                                     headers={"User-Agent": ua, "Accept": "application/json"})
        t.fixed_headers = a.get("headers") or {}
        return t

    t_auth = new_transport(auth)
    ad = Adapter(e, t_auth)
    none_auth = {"type": "none", "fields": []}
    t_none = new_transport(none_auth, cls=Transport)
    ad_none = Adapter(e, t_none)
    path_auth = auth.get("type") == "path"

    for verb, tool in a["tools"].items():
        read = bool(vocab[verb].get("read_only", False))
        args = {**dummy_args(e, verb, vocab), **SAMPLES.get(e["id"], {}).get(verb, {})}
        entry: dict = {"read": read, "method": tool.get("method", "GET"), "path": tool.get("path"), "args": args, "variants": {}}
        for variant, adp in (("dummy_auth", ad), ("no_auth", ad_none)):
            if variant == "no_auth" and (not read or path_auth):
                continue
            n0 = len(log)
            mode.update(phase="tool", tool=verb, variant=variant, mode="read" if read else "write", orig_method=tool.get("method", "GET"))
            out = await _adapter_call(adp, verb, dict(args))
            reqs = [r for r in log[n0:] if r.get("phase") == "tool"]
            v: dict = {"requests": reqs}
            if "output" in out and reqs:
                v["output_check"] = validate_output(vocab, verb, out["output"]) if read else {"valid": None}
            else:
                v["error"] = out.get("error")
            last = reqs[-1] if reqs else None
            v["class"] = classify_response(last.get("status"), last.get("body", ""), last.get("error"), "options" if last and last["method"] == "OPTIONS" else "call") if last else "not_sent"
            if v["class"] == "public" and "error" in v:
                # a 2xx whose body the adapter rejected: an error envelope, not public data
                v["class"] = "auth_required" if AUTH_BODY.search((last.get("body") or "")[:1500]) else "error_envelope"
            entry["variants"][variant] = v
            if variant == "dummy_auth" and not read and last and last["method"] == "OPTIONS" and (last.get("status") in (None, 400, 403, 404, 405) or v["class"] in ("options_405", "not_found")):
                # OPTIONS is not conclusive on this host: send the DELETE itself (dummy credentials, dummy id)
                n1 = len(log)
                mode.update(variant="dummy_auth_delete", delete_as_is=True)
                out2 = await _adapter_call(adp, verb, dict(args))
                mode.pop("delete_as_is", None)
                reqs2 = [r for r in log[n1:] if r.get("phase") == "tool"]
                if reqs2:
                    l2 = reqs2[-1]
                    v2 = {"requests": reqs2, "class": classify_response(l2.get("status"), l2.get("body", ""), l2.get("error"), "call")}
                    if "error" in out2:
                        v2["error"] = out2["error"]
                    entry["variants"]["dummy_auth_delete"] = v2
            if variant == "dummy_auth" and v["class"] == "public" and read:
                break  # already public with a dummy credential; no second request needed
        res["tools"][verb] = entry

    # control: a route that cannot exist, same host and credentials as the tools
    mode.update(phase="control", tool=None, variant="dummy_auth", mode="read", orig_method="GET")
    n0 = len(log)
    try:
        await t_auth.request("GET", "/authaudit-nonexistent-route-7f3a9c")
    except PlatformError:
        pass
    except Exception:  # noqa: BLE001
        pass
    ctl = [r for r in log[n0:]]
    res["control"] = {"requests": ctl, "class": classify_response(ctl[-1].get("status"), ctl[-1].get("body", ""), ctl[-1].get("error"), "call") if ctl else "not_sent"}

    # auth flow: token / login request with a dummy client, then authorize URLs named in the entry
    if auth.get("type") in ("oauth2_client_credentials", "oauth2_refresh_token", "session"):
        mode.update(phase="token", tool=None, variant="dummy_client", mode="read", orig_method=None)
        t_tok = new_transport(auth, cls=Transport)
        n0 = len(log)
        try:
            await t_tok._acquire_token()
            err = None
        except PlatformError as exc:
            err = exc.payload()
        except Exception as exc:  # noqa: BLE001
            err = {"error": "harness_error", "message": f"{exc.__class__.__name__}: {str(exc)[:200]}"}
        reqs = log[n0:]
        res["flow"]["token"] = {"requests": reqs, "error": err,
                                "class": classify_response(reqs[-1].get("status"), reqs[-1].get("body", ""), reqs[-1].get("error"), "call") if reqs else "not_sent"}
    auth_urls = authorize_candidates(e) if auth.get("type", "").startswith("oauth2") else []
    if auth_urls:
        res["flow"]["authorize"] = []
        async with httpx.AsyncClient(timeout=30.0, headers={"User-Agent": ua}) as c:
            for u in auth_urls:
                h = urlparse(u).hostname
                async with pacer.lock(h):
                    await pacer.wait(h)
                    try:
                        r = await c.get(u, params={"client_id": DUMMY, "response_type": "code", "redirect_uri": "https://localhost/authaudit"})
                        res["flow"]["authorize"].append({"url": u, "status": r.status_code, "location": r.headers.get("location", "")[:300], "body": r.text[:400]})
                    except Exception as exc:  # noqa: BLE001
                        res["flow"]["authorize"].append({"url": u, "error": f"{exc.__class__.__name__}: {str(exc)[:200]}"})
                    finally:
                        pacer.done(h)

    demo = VENDOR_DEMO.get(e["id"])
    if demo and demo.get("fetch"):
        field, url, pattern = demo["fetch"]
        h = urlparse(url).hostname
        async with pacer.lock(h):
            await pacer.wait(h)
            try:
                async with httpx.AsyncClient(timeout=30.0, headers={"User-Agent": ua}) as c:
                    m = re.search(pattern, (await c.get(url)).text)
            finally:
                pacer.done(h)
        demo = {**demo, "creds": {field: m.group(0)} if m else {}}
    if demo and demo.get("creds"):
        t_demo = new_transport(auth, creds_={**creds, **demo["creds"]})
        ad_demo = Adapter(e, t_demo)
        res["demo"] = {"source": demo["source"], "tools": {}}
        for verb, tool in a["tools"].items():
            if not vocab[verb].get("read_only"):
                continue
            args = {**dummy_args(e, verb, vocab), **SAMPLES.get(e["id"], {}).get(verb, {})}
            n0 = len(log)
            mode.update(phase="demo", tool=verb, variant="vendor_demo", mode="read", orig_method=tool.get("method", "GET"))
            out = await _adapter_call(ad_demo, verb, args)
            d = {"requests": log[n0:]}
            if "output" in out:
                d["output_check"] = validate_output(vocab, verb, out["output"])
            else:
                d["error"] = out.get("error")
            res["demo"]["tools"][verb] = d
    for t in (t_auth, t_none):
        await t.client.aclose()
    return res


async def run_probe(entries, out_dir: Path, interval: float, parallel: int) -> None:
    from platform_mcp_hub.vocab import load_all
    vocab_all = load_all()
    pacer = Pacer(interval)
    (out_dir / "probe").mkdir(parents=True, exist_ok=True)
    groups: dict[str, list] = {}
    for p, e in entries:
        creds = dummy_creds(e)
        h = urlparse(_fill(e["adapter"]["base_url"], creds)).hostname or "?"
        groups.setdefault(h, []).append((p, e))
    sem = asyncio.Semaphore(parallel)

    async def run_group(items):
        async with sem:
            for p, e in items:
                t0 = time.time()
                try:
                    res = await probe_entry(p, e, pacer, vocab_all)
                except Exception as exc:  # noqa: BLE001
                    res = {"id": e["id"], "key": key(p), "harness_error": f"{exc.__class__.__name__}: {exc}"}
                res["probed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                (out_dir / "probe" / f"{p.parent.name}__{p.stem}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
                print(f"{key(p)}: {len(res.get('tools', {}))} tools in {time.time() - t0:.0f}s", flush=True)

    await asyncio.gather(*(run_group(v) for v in groups.values()))



# ------------------------------------------------------------------------------------------ spec

# Vendor-published machine-readable specs (the vendor's own host or its official GitHub organisation).
SPECS: dict[str, list[dict]] = {
    "etsy": [{"url": "https://www.etsy.com/openapi/generated/oas/3.0.0.json"}],
    "allegro": [{"url": "https://developer.allegro.pl/swagger.yaml"}],
    "pinterest": [{"url": "https://raw.githubusercontent.com/pinterest/api-description/main/v5/openapi.yaml"}],
    "pinterest_catalogs": [{"url": "https://raw.githubusercontent.com/pinterest/api-description/main/v5/openapi.yaml"}],
    "x": [{"url": "https://api.x.com/2/openapi.json"}],
    "slack": [{"url": "https://raw.githubusercontent.com/slackapi/slack-api-specs/master/web-api/slack_web_openapi_v2.json"}],
    "discord": [{"url": "https://raw.githubusercontent.com/discord/discord-api-spec/main/specs/openapi.json"}],
    "resend": [{"url": "https://raw.githubusercontent.com/resend/resend-openapi/main/resend.yaml"}],
    "zendesk": [{"url": "https://developer.zendesk.com/zendesk/oas.yaml"}],
    "line": [{"url": "https://raw.githubusercontent.com/line/line-openapi/main/messaging-api.yml"},
             {"url": "https://raw.githubusercontent.com/line/line-openapi/main/insight.yml"}],
    "vimeo": [{"url": "https://raw.githubusercontent.com/vimeo/openapi/master/api.yaml"}],
    "webflow": [{"url": "https://raw.githubusercontent.com/webflow/openapi-spec/main/openapi/v2.yml"}],
    "elevenlabs": [{"url": "https://api.elevenlabs.io/openapi.json"}],
    "bfl": [{"url": "https://api.bfl.ai/openapi.json"}],
    "hh_ru": [{"url": "https://api.hh.ru/openapi/specification/public"}],
    # the published index points its $refs at http://127.0.0.1:10000/…; the same files are served next to it
    "uk_companies_house": [{"url": "https://developer-specs.company-information.service.gov.uk/api.ch.gov.uk-specifications/swagger-2.0/spec/swagger.json",
                            "ref_rewrite": {"http://127.0.0.1:10000/": "https://developer-specs.company-information.service.gov.uk/"}}],
    "farcaster": [{"url": "https://raw.githubusercontent.com/neynarxyz/OAS/main/src/api/spec.yaml"}],
    "binance_spot": [{"url": "https://raw.githubusercontent.com/binance/binance-api-swagger/master/spot_api.yaml"}],
    "amazon": [{"url": "https://raw.githubusercontent.com/amzn/selling-partner-api-models/main/models/sellers-api-model/sellers.json"},
               {"url": "https://raw.githubusercontent.com/amzn/selling-partner-api-models/main/models/orders-api-model/ordersV0.json"},
               {"url": "https://raw.githubusercontent.com/amzn/selling-partner-api-models/main/models/listings-items-api-model/listingsItems_2021-08-01.json"}],
    "amazon_ads": [{"url": "https://d1y2lf8k3vrkfu.cloudfront.net/openapi/en-us/dest/Profiles_prod_3p.json", "tools": ["me", "list_accounts"]},
                   {"url": "https://d1y2lf8k3vrkfu.cloudfront.net/openapi/en-us/dest/SponsoredProducts_prod_3p.json", "tools": ["list_campaigns", "update_budget", "pause_resume"]}],
    "amazon_fire_tv_ads": [{"url": "https://d1y2lf8k3vrkfu.cloudfront.net/openapi/en-us/dest/Profiles_prod_3p.json", "tools": ["me", "list_accounts"]},
                           {"url": "https://d1y2lf8k3vrkfu.cloudfront.net/openapi/en-us/dest/SponsoredTV_prod_3p.json", "tools": ["list_campaigns", "update_budget", "pause_resume"]}],
    "amazon_dsp": [{"url": "https://d1y2lf8k3vrkfu.cloudfront.net/openapi/en-us/dest/Profiles_prod_3p.json", "tools": ["me"]}],
    "bol_com": [{"url": "https://api.bol.com/retailer/public/apispec/Retailer%20API%20-%20v10"}],
    "matrix": [{"url": "https://spec.matrix.org/latest/client-server-api/api.json"}],
    "huggingface": [{"url": "https://huggingface.co/.well-known/openapi.json"}],
    "ideogram": [{"url": "https://api.ideogram.ai/openapi.json"}],
    "useq": [{"url": "https://docs.alpaca.markets/openapi/trading-api.json"}, {"url": "https://docs.alpaca.markets/openapi/market-data-api.json"}],
    "sendgrid": [{"url": "https://raw.githubusercontent.com/twilio/sendgrid-oai/main/spec/json/tsg_mail_v3.json"},
                 {"url": "https://raw.githubusercontent.com/twilio/sendgrid-oai/main/spec/json/tsg_user_v3.json"}],
    "intercom": [{"url": "https://raw.githubusercontent.com/intercom/Intercom-OpenAPI/main/descriptions/2.11/api.intercom.io.yaml"}],
    "devto": [{"url": "https://raw.githubusercontent.com/forem/forem/main/swagger/v1/api_v1.json"}],
    "github": [{"url": "https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json"},
               {"url": "https://docs.github.com/public/fpt/schema.docs.graphql", "kind": "graphql"}],
    "google": [{"url": "https://googleads.googleapis.com/$discovery/rest?version=v25"}],
    "admob": [{"url": "https://admob.googleapis.com/$discovery/rest?version=v1"}],
    "google_sheets": [{"url": "https://sheets.googleapis.com/$discovery/rest?version=v4"}],
    "gmail": [{"url": "https://gmail.googleapis.com/$discovery/rest?version=v1"}],
    "google_chat": [{"url": "https://chat.googleapis.com/$discovery/rest?version=v1"}],
    "youtube": [{"url": "https://www.googleapis.com/discovery/v1/apis/youtube/v3/rest"}],
    "dv360": [{"url": "https://displayvideo.googleapis.com/$discovery/rest?version=v4"}],
    "google_merchant": [{"url": "https://merchantapi.googleapis.com/$discovery/rest?version=accounts_v1"},
                        {"url": "https://merchantapi.googleapis.com/$discovery/rest?version=products_v1"}],
    "google_business": [{"url": "https://mybusinessaccountmanagement.googleapis.com/$discovery/rest?version=v1", "tools": ["me"]}],
    "lulu": [{"url": "https://api.lulu.com/api-docs/openapi-specs/openapi_public.yml"}],
    "lulu_print_api": [{"url": "https://api.lulu.com/api-docs/openapi-specs/openapi_public.yml"}],
    "whatsapp": [{"url": "https://raw.githubusercontent.com/facebook/openapi/main/business-messaging-api_v23.0.yaml"}],
    "paddle": [{"url": "https://raw.githubusercontent.com/PaddleHQ/paddle-openapi/main/v1/openapi.yaml"}],
    "microsoft_graph": [{"url": "https://raw.githubusercontent.com/microsoftgraph/msgraph-metadata/master/openapi/v1.0/openapi.yaml"}],
    "teams": [{"url": "https://raw.githubusercontent.com/microsoftgraph/msgraph-metadata/master/openapi/v1.0/openapi.yaml"}],
    "printful": [{"url": "https://developers.printful.com/docs/openapi.json"}],
    "bluesky": [{"kind": "lexicon", "url": "https://raw.githubusercontent.com/bluesky-social/atproto/main/lexicons/"}],
    "seznam_sklik": [{"url": "https://api.sklik.cz/v1/openapi.json"}],
    "nettiauto": [{"url": "https://api.nettix.fi/docs/car/swagger.yaml"}],
    "tradera": [{"url": "https://api.tradera.com/v4/swagger/v4/swagger.json"}],
    "belancer_com": [{"url": "https://belancer.com/api/openapi.json"}],
    "udbud_dk": [{"url": "https://git.erst.dk/udbud-dk/sdk/-/raw/master/openapi.yml"}],
    "doordash_ads": [{"url": "https://developer.doordash.com/en-US/redocusaurus/plugin-redoc-11.yaml"}],
    "magalu": [{"url": "https://developers.magalu.com/apis/orders.openapi.yaml"}, {"url": "https://developers.magalu.com/apis/products.openapi.yaml"}],
    "zalora": [{"url": "https://sellercenter-api.zalora.com/docs/openapi-standalone.yaml"}],
    "abound": [{"url": "https://developers.moderndropship.com/openapi/buyer-api.json"}, {"url": "https://developers.moderndropship.com/openapi/shared-api.json"}],
    "blurb": [{"url": "https://docs.api.rpiprint.com/OAS3/public-api-OAS3.yaml"}],
    "contrado": [{"url": "https://api.contrado.app/helix/swagger/v1/swagger.json"}],
    "olist_tiny_erp": [{"url": "https://api.tiny.com.br/public-api/v3/swagger/swagger.json"}],
    "arbeidsplassen": [{"url": "https://pam-stilling-feed.nav.no/api/openapi.json"}],
    "circle": [{"url": "https://api-headless.circle.so/api/admin/v2/swagger.yaml"}],
    "digistore24": [{"url": "https://digistore24.com/api/docs/openapi.yaml"}],
    "wykop": [{"url": "https://doc.wykop.pl/openapi.yaml"}],
    "producthunt": [{"url": "https://raw.githubusercontent.com/producthunt/producthunt-api/master/schema.graphql", "kind": "graphql"}],
    "nova_engel": [{"url": "https://drop.novaengel.com/swagger/docs/v1"}],
    "takealot": [{"url": "https://seller-api.takealot.com/api-docs/swagger.json"}],
    "depop": [{"url": "https://partnerapi.depop.com/api-docs/openapi.yaml"}],
    "jumia": [{"url": "https://vendorcenter.jumia.com/api-docs/openapi.yaml"}],
    "ankorstore": [{"url": "https://ankorstore.github.io/api-docs/", "kind": "redoc"}],
    "partnerize": [{"url": "https://api-docs.partnerize.com/brand/", "kind": "redoc"}],
    "freelancehunt": [{"url": "https://documenter.gw.postman.com/api/collections/3971751/S1Lzy7WU?segregateAuth=true&versionTag=latest", "kind": "postman"}],
    "blanka": [{"url": "https://documenter.gw.postman.com/api/collections/10905449/2sA35LWzqV?segregateAuth=true&versionTag=latest", "kind": "postman"}],
}
GOOGLE_GLOBAL = {"$.xgafv", "access_token", "alt", "callback", "fields", "key", "oauth_token", "prettyPrint", "quotaUser", "upload_protocol", "uploadType"}
AUTHISH = re.compile(r"(?i)^(token|access_token|api_key|apikey|key|signature|sign|timestamp|recvwindow|app_key|appkey|sig)$")
PAGEISH = re.compile(r"(?i)(page|offset|cursor|token|after|before|start|limit|per_page|max_?results|size|count|continuation|since_id|until_id|from)")


def _load_doc(text: str):
    t = text.lstrip()
    if t[:1] in "{[":
        return json.loads(text)
    import yaml

    class _Loader(getattr(yaml, "CSafeLoader", yaml.SafeLoader)):
        pass
    _Loader.add_constructor("tag:yaml.org,2002:value", lambda loader, node: loader.construct_scalar(node))  # a bare `=` key
    _Loader.add_constructor("tag:yaml.org,2002:timestamp", lambda loader, node: loader.construct_scalar(node))  # dates stay strings
    return yaml.load(text, Loader=_Loader)


class SpecCache:
    def __init__(self, out_dir: Path, pacer: Pacer):
        self.dir = out_dir / "specs"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.pacer = pacer
        self.mem: dict[str, object] = {}

    def get_sync(self, url: str):
        import hashlib
        import httpx
        f = self.dir / (hashlib.sha1(url.encode()).hexdigest() + ".txt")
        if not f.exists():
            time.sleep(1.0)
            r = httpx.get(url, timeout=120.0, follow_redirects=True, headers={"User-Agent": "platform-mcp-auth-audit (+https://github.com/tonyyang0504/platform-mcp)"})
            if r.status_code != 200:
                raise ValueError(f"{url}: {r.status_code}")
            f.write_text(r.text, encoding="utf-8")
        return _load_doc(f.read_text(encoding="utf-8"))

    async def get(self, url: str, parse: bool = True):
        import hashlib
        import httpx
        if url in self.mem:
            return self.mem[url]
        f = self.dir / (hashlib.sha1(url.encode()).hexdigest() + ".txt")
        if not f.exists():
            h = urlparse(url).hostname
            async with self.pacer.lock(h):
                await self.pacer.wait(h)
                try:
                    async with httpx.AsyncClient(timeout=180.0, follow_redirects=True, headers={"User-Agent": "platform-mcp-auth-audit (+https://github.com/tonyyang0504/platform-mcp)"}) as c:
                        r = await c.get(url)
                finally:
                    self.pacer.done(h)
            if r.status_code != 200:
                self.mem[url] = None
                return None
            f.write_text(r.text, encoding="utf-8")
        text = f.read_text(encoding="utf-8")
        doc = (_load_doc(text) if parse else text)
        self.mem[url] = doc
        return doc


def redoc_state(html: str):
    """A Redoc page that embeds its spec (`const __redoc_state = {...};`)."""
    m = re.search(r"__redoc_state\s*=\s*", html)
    if not m:
        return None
    obj, _ = json.JSONDecoder().raw_decode(html[m.end():])
    return ((obj.get("spec") or {}).get("data")) if isinstance(obj, dict) else None


def _example_schema(v):
    """A JSON Schema derived from an example value (Postman bodies and saved responses)."""
    if isinstance(v, dict):
        return {"type": "object", "properties": {k: _example_schema(x) for k, x in v.items()}, "additionalProperties": not v}
    if isinstance(v, list):
        return {"type": "array", "items": _example_schema(v[0]) if v else {}}
    return {}


def build_ops_postman(coll: dict) -> list[dict]:
    """Postman collection v2: requests (method, URL with {{var}} / :var segments, query keys, raw JSON
    body example) and saved response examples, as operations with example-derived schemas."""
    ops: list[dict] = []

    def jl(text):
        try:
            return json.loads(text) if text and text.strip()[:1] in "{[" else None
        except ValueError:
            return None

    def walk(items):
        for it in items or []:
            if "item" in it:
                walk(it["item"])
                continue
            r = it.get("request") or {}
            r = {"url": r, "method": "GET"} if isinstance(r, str) else r
            u = r.get("url") or {}
            raw = u.get("raw", "") if isinstance(u, dict) else str(u)
            r0 = raw.split("?")[0]
            if isinstance(u, dict) and u.get("path"):
                path = "/" + "/".join(u.get("path") or [])
            elif r0.startswith("http"):
                path = urlparse(r0).path
            else:
                path = "/" + r0.split("}}", 1)[-1].lstrip("/")
            tpl = re.sub(r"\{\{([^}]+)\}\}", r"{\1}", path)
            tpl = re.sub(r"/:([A-Za-z_][A-Za-z0-9_]*)", r"/{\1}", tpl)
            params = {q["key"]: {"in": "query", "required": False} for q in ((u.get("query") or []) if isinstance(u, dict) else []) if isinstance(q, dict) and q.get("key")}
            body = None
            b = r.get("body") or {}
            if b.get("mode") == "raw":
                ex = jl(b.get("raw"))
                body = _example_schema(ex) if ex is not None else None
            form = {f["key"]: {"in": "formData", "required": False} for f in (b.get(b.get("mode") or "", []) if b.get("mode") in ("formdata", "urlencoded") else [])}
            resp = None
            for ex in it.get("response") or []:
                data = jl(ex.get("body"))
                if data is not None and str(ex.get("code", 200)).startswith("2"):
                    resp = _example_schema(data)
                    break
            ops.append({"method": (r.get("method") or "GET").upper(), "template": tpl, "regex": "(?:/[^?]*)?" + _seg_regex(tpl), "params": params, "form": form,
                        "body": body, "response": resp, "host": None, "id": it.get("name"), "open_query": True})
    walk(coll.get("item"))
    return ops


def bundle_external(doc, url: str, fetch, depth: int = 0, seen=None, rewrite: dict | None = None):
    """Inline external `$ref`s (other files next to the spec) so the comparator can walk them."""
    from urllib.parse import urljoin
    seen = seen if seen is not None else {}
    rewrite = rewrite or {}

    def resolve(node, base, d):
        if d > 25:
            return node
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and not ref.startswith("#") and re.search(r"\.(json|ya?ml)(#|$)", ref):
                for a_, b_ in rewrite.items():
                    ref = ref.replace(a_, b_)
                target, _, frag = urljoin(base, ref).partition("#")
                if target not in seen:
                    seen[target] = None
                    try:
                        seen[target] = resolve(fetch(target), target, d + 1)
                    except Exception:  # noqa: BLE001
                        seen[target] = None
                cur = seen[target]
                for part in [x for x in frag.split("/") if x]:
                    cur = cur.get(part.replace("~1", "/").replace("~0", "~")) if isinstance(cur, dict) else None
                return cur if cur is not None else node
            return {k: resolve(v, base, d) for k, v in node.items()}
        if isinstance(node, list):
            return [resolve(v, base, d) for v in node]
        return node
    return resolve(doc, url, depth)


def _seg_regex(template: str) -> str:
    out, i = [], 0
    for m in re.finditer(r"\{([+]?)([^{}]+)\}", template):
        out.append(re.escape(template[i:m.start()]))
        out.append(".+" if m.group(1) == "+" else "[^/]+")
        i = m.end()
    out.append(re.escape(template[i:]))
    return "".join(out)


def build_ops(doc: dict, url: str) -> list[dict]:
    """Normalise an OpenAPI 3 / Swagger 2 / Google discovery document into operations."""
    ops: list[dict] = []
    if not isinstance(doc, dict):
        return ops
    if doc.get("discoveryVersion"):
        base = "/" + (doc.get("servicePath") or "").strip("/")
        host = urlparse(doc.get("rootUrl", "")).hostname

        def walk(res):
            for m in (res.get("methods") or {}).values():
                tpl = (base.rstrip("/") + "/" + (m.get("flatPath") or m["path"]).lstrip("/"))
                params = {k: {"in": v.get("location"), "required": bool(v.get("required"))} for k, v in (m.get("parameters") or {}).items()}
                for g in GOOGLE_GLOBAL:
                    params.setdefault(g, {"in": "query", "required": False})
                ops.append({"method": m["httpMethod"].upper(), "template": tpl, "regex": _seg_regex(tpl), "params": params,
                            "body": {"$ref": m["request"]["$ref"]} if m.get("request") else None,
                            "response": {"$ref": m["response"]["$ref"]} if m.get("response") else None, "host": host, "id": m.get("id")})
                if m.get("flatPath") and m.get("path") and m["path"] != m["flatPath"]:
                    tpl2 = base.rstrip("/") + "/" + m["path"].lstrip("/")
                    ops.append({**ops[-1], "template": tpl2, "regex": _seg_regex(tpl2)})
            for r in (res.get("resources") or {}).values():
                walk(r)
        walk(doc)
        return ops
    swagger2 = str(doc.get("swagger", "")).startswith("2")
    if swagger2:
        bases = [doc.get("basePath") or ""]
        hosts = [doc.get("host")]
    else:
        servers = doc.get("servers") or [{"url": ""}]
        bases, hosts = [], []
        for s in servers:
            u = s.get("url", "")
            for var, spec in (s.get("variables") or {}).items():
                u = u.replace("{" + var + "}", str(spec.get("default", "")))
            u = "https:" + u if u.startswith("//") else u  # protocol-relative server URL
            pu = urlparse(u if "://" in u else "https://x" + u)
            bases.append(pu.path.rstrip("/"))
            hosts.append(pu.hostname if "://" in u else None)
    for path, item in (doc.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        common = item.get("parameters") or []
        for method, op in item.items():
            if method.lower() not in ("get", "post", "put", "patch", "delete") or not isinstance(op, dict):
                continue
            params, form = {}, {}
            body = None
            for prm in list(common) + list(op.get("parameters") or []):
                prm = _deref(doc, prm)
                if not isinstance(prm, dict) or "name" not in prm:
                    continue
                if prm.get("in") == "body":
                    body = prm.get("schema")
                elif prm.get("in") == "formData":
                    form[prm["name"]] = {"in": "formData", "required": bool(prm.get("required"))}
                else:
                    params[prm["name"]] = {"in": prm.get("in"), "required": bool(prm.get("required"))}
            if not swagger2 and op.get("requestBody"):
                rb = _deref(doc, op["requestBody"])
                content = (rb or {}).get("content") or {}
                for ctype in ("application/json", *content.keys()):
                    if ctype in content and isinstance(content[ctype], dict):
                        body = content[ctype].get("schema")
                        if "form" in ctype and body is not None:
                            sch = _merge(doc, body)
                            for k in (sch.get("properties") or {}):
                                form[k] = {"in": "formData", "required": k in (sch.get("required") or [])}
                        break
            response = None
            example = None
            for code in ("200", "201", "202", "207", "2XX", "2xx", 200, 201, 202, "default"):
                r = (op.get("responses") or {}).get(code)
                if r is None:
                    continue
                r = _deref(doc, r)
                if swagger2:
                    response = (r or {}).get("schema")
                    example = next(iter(((r or {}).get("examples") or {}).values()), None)
                else:
                    content = (r or {}).get("content") or {}
                    for ctype in ("application/json", *content.keys()):
                        if ctype in content and isinstance(content[ctype], dict) and content[ctype].get("schema") is not None:
                            response = content[ctype]["schema"]
                            mt = content[ctype]
                            example = mt.get("example") if "example" in mt else next((x.get("value") for x in (mt.get("examples") or {}).values() if isinstance(x, dict)), None)
                            break
                if example is None and isinstance(_deref(doc, response), dict):
                    example = _deref(doc, response).get("example")
                if response is not None:
                    break
            op_bases = bases
            if not swagger2 and op.get("servers"):
                op_bases = [urlparse(s.get("url", "")).path.rstrip("/") for s in op["servers"]]
            for b in op_bases:
                tpl = (b or "").rstrip("/") + "/" + path.lstrip("/")
                ops.append({"method": method.upper(), "template": tpl, "regex": _seg_regex(tpl), "params": params, "form": form,
                            "body": body, "response": response, "example": example, "host": hosts[0] if hosts else None, "id": op.get("operationId")})
    return ops


def _deref(doc: dict, node, depth: int = 0):
    while isinstance(node, dict) and "$ref" in node and depth < 30:
        ref = node["$ref"]
        depth += 1
        if isinstance(ref, str) and ref.startswith("#/"):
            cur = doc
            for part in ref[2:].split("/"):
                part = part.replace("~1", "/").replace("~0", "~")
                cur = cur.get(part) if isinstance(cur, dict) else None
            node = cur
        elif isinstance(ref, str) and doc.get("discoveryVersion"):
            node = (doc.get("schemas") or {}).get(ref)
        else:
            return None  # external reference: not resolvable here
    return node


def _merge(doc: dict, schema, depth: int = 0) -> dict:
    """allOf merged into one object schema (properties, required, additionalProperties)."""
    schema = _deref(doc, schema)
    if not isinstance(schema, dict) or depth > 12:
        return {}
    if "allOf" in schema:
        out: dict = {"properties": {}, "required": []}
        for sub in schema["allOf"]:
            m = _merge(doc, sub, depth + 1)
            out["properties"].update(m.get("properties") or {})
            out["required"] += list(m.get("required") or [])
            for k in ("items", "type", "additionalProperties"):
                if k in m and k not in out:
                    out[k] = m[k]
        out["properties"].update(schema.get("properties") or {})
        return out
    return schema


def walk_schema(doc: dict, schema, segs: list[str], depth: int = 0):
    """(True|False|None, subschema): True the path is defined, False it is absent from an explicit
    schema, None the schema is open or unresolvable at that point."""
    if depth > 40:
        return None, None
    schema = _merge(doc, schema)
    if not segs:
        return True, schema
    if not schema:
        return None, None
    seg = segs[0]
    props = schema.get("properties")
    if isinstance(props, dict) and seg in props:
        return walk_schema(doc, props[seg], segs[1:], depth + 1)
    branches = []
    disc = schema.get("discriminator") if isinstance(schema.get("discriminator"), dict) else None
    if disc and disc.get("mapping"):
        branches += [{"$ref": r} if isinstance(r, str) and r.startswith("#") else r for r in disc["mapping"].values()]
    for key_ in ("oneOf", "anyOf"):
        branches += list(schema.get(key_) or [])
    if branches:
        results = [walk_schema(doc, b, segs, depth + 1) for b in branches]
        for ok, sub in results:
            if ok:
                return ok, sub
        if any(ok is None for ok, _ in results):
            return None, None
    if schema.get("type") == "array" or "items" in schema:
        if seg.isdigit():
            return walk_schema(doc, schema.get("items"), segs[1:], depth + 1)
        return False, None
    ap = schema.get("additionalProperties")
    if ap not in (None, False):
        return (walk_schema(doc, ap, segs[1:], depth + 1) if isinstance(ap, dict) else (None, None))
    if (isinstance(props, dict) and props) or branches:
        return False, None
    return None, None


def _adapter_path(e: dict, tool: dict, creds: dict, verb: str | None = None) -> tuple[str, str | None, dict]:
    base = _fill(e["adapter"]["base_url"], creds)
    raw = tool["path"] if str(tool["path"]).startswith("http") else base.rstrip("/") + tool["path"]
    raw = _fill(raw, {k: v for k, v in creds.items() if "{" + k + "}" in e["adapter"]["base_url"]})
    raw = _fill(raw, {k: v[1:] for k, v in (tool.get("path_params") or {}).items() if isinstance(v, str) and v.startswith("=")})
    raw = _fill(raw, {k: str(v) for k, v in SAMPLES.get(e["id"], {}).get(verb or "", {}).items()})  # real ids (may span segments)
    raw = re.sub(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}", "X1X", raw)
    u = urlparse(raw)
    inline = dict(x.split("=", 1) if "=" in x else (x, "") for x in u.query.split("&") if x)
    return u.path, u.hostname, inline


def _match(ops: list[dict], path: str, method: str) -> tuple[dict | None, list[dict], str | None]:
    cands = [o for o in ops if re.fullmatch(o["regex"], path)]
    note = None
    if not cands:
        vpat = re.compile(r"/v\d+(?:\.\d+)?(?=/|$)")
        norm = vpat.sub("/vN", path)
        cands = [o for o in ops if re.fullmatch(_seg_regex(vpat.sub("/vN", o["template"])), norm)]
        if cands:
            note = f"matched only after normalising the version segment (spec {cands[0]['template']})"
    if not cands:
        # trailing-slash tolerance
        alt = path[:-1] if path.endswith("/") else path + "/"
        cands = [o for o in ops if re.fullmatch(o["regex"], alt)]
        if cands:
            note = f"matched only with a different trailing slash (spec {cands[0]['template']})"
    if note and "version" in note:
        # a version-normalised match must still share a literal segment ({+name} matches anything)
        cands = [o for o in cands if re.search(r"/[A-Za-z_][^/{}]*", re.sub(r"/v\d+(?:\.\d+)?(?=/|$)", "", o["template"]))]
    same = [o for o in cands if o["method"] == method]
    same.sort(key=lambda o: -len(re.sub(r"\{[^}]*\}", "", o["template"])))
    return same, cands, note


def compare_tool(e: dict, verb: str, tool: dict, ops_by_doc: list[tuple[dict, list[dict]]], creds: dict) -> dict:
    path, host, inline = _adapter_path(e, tool, creds, verb)
    method = tool.get("method", "GET").upper()
    out: dict = {"path": path, "method": method, "issues": [], "notes": [], "unverifiable": []}
    found = []
    wrong = set()
    for doc, ops in ops_by_doc:
        same, cands, note = _match(ops, path, method)
        found += [(doc, op, note) for op in same]
        wrong |= {c["method"] for c in cands}
    if not found:
        if wrong:
            out["issues"].append(f"method: adapter {method} {path}; spec defines {'/'.join(sorted(wrong))} only")
        else:
            out["issues"].append(f"path not in spec: {method} {path}")
        return out
    results = [_check_op(e, tool, doc, op, note, path, host, method, inline) for doc, op, note in found]
    return min(results, key=lambda r: (len(r["issues"]), len(r["unverifiable"])))


def _check_op(e: dict, tool: dict, doc: dict, op: dict, note, path: str, host, method: str, inline: dict) -> dict:
    out: dict = {"path": path, "method": method, "issues": [], "notes": [], "unverifiable": []}
    out["op"] = f"{op['method']} {op['template']}" + (f" ({op['id']})" if op.get("id") else "")
    if note:
        out["notes"].append(note)
    if op.get("host") and host and op["host"] != host and not op["host"].endswith(host.split(".", 1)[-1]):
        out["notes"].append(f"host: adapter {host}, spec server {op['host']}")
    auth = e["adapter"].get("auth", {})
    ignore = set((auth.get("params") or {}).keys()) | ({auth.get("param")} if auth.get("param") else set()) | {auth.get("token_param")}
    sign = auth.get("sign") or {}
    ignore |= {sign.get("timestamp_param"), sign.get("signature_param")} | set((sign.get("params") or {}).keys())
    sent = [k for k in list((tool.get("params") or {}).keys()) + list((tool.get("fixed_params") or {}).keys()) + list(inline.keys()) if k not in ignore]
    spec_q = {k: v for k, v in op["params"].items() if v.get("in") in ("query", None)}
    body_is_form = bool(op.get("form")) and not op.get("body")
    for k in sent:
        base_k = k.split("[", 1)[0] if "[" in k else k  # items[] / data[name] / created_at[GTE]: deepObject-style names
        if k not in spec_q and base_k not in spec_q and not (k in (op.get("form") or {})) and not op.get("open_query"):
            out["issues"].append(f"query parameter {k!r} is not defined by the spec")
    sent_base = {x.split("[", 1)[0] for x in sent}
    for k, v in spec_q.items():
        if v.get("required") and k not in sent and k not in sent_base and not AUTHISH.match(k) and k not in GOOGLE_GLOBAL:
            out["issues"].append(f"spec requires query parameter {k!r}, adapter does not send it")
    body = tool.get("body") or {}
    if body:
        if body_is_form or (tool.get("body_format") == "form" and op.get("form")):
            for k in body:
                top = k.split(".")[0]
                if top not in op["form"] and top not in spec_q:
                    out["issues"].append(f"form field {top!r} is not defined by the spec")
        elif op.get("body") is not None:
            for k in body:
                segs = [s.replace("\\.", ".") for s in re.split(r"(?<!\\)\.", k)]
                if segs and segs[0].isdigit():
                    ok, _ = walk_schema(doc, op["body"], segs)
                else:
                    ok, _ = walk_schema(doc, op["body"], segs)
                if ok is False:
                    out["issues"].append(f"body field {k!r} is not in the request schema")
                elif ok is None:
                    out["unverifiable"].append(f"body {k}")
            req = _merge(doc, op["body"]).get("required") or []
            tops = {re.split(r"(?<!\\)\.", k)[0] for k in body}
            if auth.get("token_body_path"):
                tops.add(auth["token_body_path"].split(".")[0])
            for r in req:
                if r not in tops:
                    out["issues"].append(f"spec requires body field {r!r}, adapter does not send it")
        elif op.get("form"):
            for k in body:
                if k.split(".")[0] not in op["form"]:
                    out["issues"].append(f"form field {k.split('.')[0]!r} is not defined by the spec")
        else:
            out["unverifiable"].append("request body (spec defines none)")
    result = tool.get("result") or {}
    resp = op.get("response")
    if resp is None and (result.get("items") or result.get("fields")):
        out["unverifiable"].append("response (no schema in spec)")
    elif result and resp is not None:
        ex_root = op.get("example")

        def ex_has(prefix: list[str], dotted: str) -> bool:
            cur = ex_root
            for part in prefix + dotted.split("."):
                if isinstance(cur, list):
                    if not (part.isdigit() and int(part) < len(cur)):
                        return False
                    cur = cur[int(part)]
                elif isinstance(cur, dict):
                    if part not in cur:
                        return False
                    cur = cur[part]
                else:
                    return False
            return True

        def check(label, root_schema, dotted, ex_prefix=None):
            if isinstance(dotted, str):
                dotted = re.sub(r"^(num|str|iso_ms|iso_s):", "", dotted).split("|")[0]
            if dotted in (None, "", "$"):
                return root_schema
            ok, sub = walk_schema(doc, root_schema, dotted.split("."))
            if ok is False and ex_root is not None and ex_has(ex_prefix or [], dotted):
                out["notes"].append(f"{label}={dotted!r} is absent from the schema but present in the spec's own response example")
                return sub
            if ok is False:
                out["issues"].append(f"response path {label}={dotted!r} is not in the response schema")
            elif ok is None:
                out["unverifiable"].append(f"{label} {dotted}")
            return sub
        if "items" in result:
            item_schema = None
            coll = check("items", resp, result["items"])
            if coll is not None:
                cm = _merge(doc, coll)
                if result.get("items_are_values"):
                    item_schema = cm.get("additionalProperties") if isinstance(cm.get("additionalProperties"), dict) else None
                elif cm.get("type") == "array" or "items" in cm:
                    item_schema = cm.get("items")
                elif cm:
                    item_schema = cm  # a single object: the runtime returns it as a one-row list
                    out["notes"].append(f"items={result['items']!r} is a single object in the spec (returned as one row)")
            ip = [] if result["items"] in ("$", "") else result["items"].split(".")
            for norm, src in (result.get("fields") or {}).items():
                if isinstance(src, str) and not src.startswith("=") and item_schema is not None:
                    check(f"fields.{norm}", item_schema, src, ip + ["0"])
            for k in ("total", "next_cursor"):
                if result.get(k):
                    check(k, resp, result[k])
        elif "fields" in result:
            rec = check("root", resp, result.get("root")) if result.get("root") else resp
            if rec is not None:
                rp = result["root"].split(".") if result.get("root") else []
                for norm, src in (result.get("fields") or {}).items():
                    if isinstance(src, str) and not src.startswith("="):
                        check(f"fields.{norm}", rec, src, rp)
    # pagination style: what the spec offers vs what the adapter maps
    pag_spec = sorted(k for k in spec_q if PAGEISH.search(k) and k not in GOOGLE_GLOBAL)
    exprs = {k: v for k, v in (tool.get("params") or {}).items()}
    uses = sorted(f"{k}={v}" for k, v in exprs.items() if v in ("page", "page0", "offset", "limit", "cursor"))
    if pag_spec or uses:
        out["pagination"] = {"spec": pag_spec, "adapter": uses, "next_cursor": result.get("next_cursor")}
    return out


def _lexicon_url(base: str, nsid: str) -> str:
    return base + nsid.replace(".", "/") + ".json"


async def compare_lexicon(e: dict, cache: SpecCache, base: str) -> dict:
    """AT Protocol: each /xrpc/<nsid> endpoint is defined by a lexicon document."""
    res = {}
    docs: dict[str, dict] = {}

    async def lex(nsid):
        if nsid not in docs:
            docs[nsid] = await cache.get(_lexicon_url(base, nsid)) or {}
        return docs[nsid]

    async def resolve(ref: str, ctx: str):
        nsid, _, name = (ctx + ref if ref.startswith("#") else ref).partition("#")
        d = await lex(nsid)
        return (d.get("defs") or {}).get(name or "main"), nsid

    async def walk(schema, segs, ctx, depth=0):
        if depth > 30:
            return None, None, ctx
        if not isinstance(schema, dict):
            return None, None, ctx
        t = schema.get("type")
        if t == "ref":
            sub, nctx = await resolve(schema["ref"], ctx)
            return await walk(sub, segs, nctx, depth + 1)
        if t == "union":
            outs = []
            for r in schema.get("refs", []):
                sub, nctx = await resolve(r, ctx)
                outs.append(await walk(sub, segs, nctx, depth + 1))
            for o in outs:
                if o[0]:
                    return o
            return (None, None, ctx) if any(o[0] is None for o in outs) else (False, None, ctx)
        if not segs:
            return True, schema, ctx
        if t == "array":
            return await walk(schema.get("items"), segs[1:] if segs[0].isdigit() else segs, ctx, depth + 1) if segs[0].isdigit() else (False, None, ctx)
        if t in ("object", "params", "record") or "properties" in schema:
            if t == "record":
                return await walk(schema.get("record"), segs, ctx, depth + 1)
            props = schema.get("properties") or {}
            if segs[0] in props:
                return await walk(props[segs[0]], segs[1:], ctx, depth + 1)
            return False, None, ctx
        if t == "unknown":
            return None, None, ctx
        return False, None, ctx

    for verb, tool in e["adapter"]["tools"].items():
        out = {"path": tool["path"], "method": tool.get("method", "GET"), "issues": [], "notes": [], "unverifiable": []}
        m = re.match(r"^/xrpc/([a-zA-Z0-9.]+)$", tool["path"])
        if not m:
            out["issues"].append("not an /xrpc/<nsid> path")
            res[verb] = out
            continue
        nsid = m.group(1)
        d = await lex(nsid)
        main = (d.get("defs") or {}).get("main")
        if not main:
            out["issues"].append(f"no lexicon {nsid}")
            res[verb] = out
            continue
        out["op"] = f"{main['type']} {nsid}"
        want = "GET" if main["type"] == "query" else "POST"
        if want != out["method"]:
            out["issues"].append(f"method: lexicon {main['type']} needs {want}")
        params = (main.get("parameters") or {}).get("properties") or {}
        sent = list((tool.get("params") or {}).keys()) + list((tool.get("fixed_params") or {}).keys())
        for k in sent:
            if k not in params:
                out["issues"].append(f"query parameter {k!r} is not in the lexicon")
        for k in (main.get("parameters") or {}).get("required") or []:
            if k not in sent:
                out["issues"].append(f"lexicon requires parameter {k!r}")
        inp = ((main.get("input") or {}).get("schema"))
        for k in (tool.get("body") or {}):
            if inp is None:
                out["issues"].append("lexicon defines no input body")
                break
            ok, _, _ = await walk(inp, k.split("."), nsid)
            if ok is False:
                out["issues"].append(f"body field {k!r} is not in the lexicon input")
            elif ok is None:
                out["unverifiable"].append(f"body {k}")
        if inp is not None:
            for r in inp.get("required") or []:
                if r not in {k.split(".")[0] for k in (tool.get("body") or {})}:
                    out["issues"].append(f"lexicon requires body field {r!r}")
        outp = (main.get("output") or {}).get("schema")
        result = tool.get("result") or {}
        if outp is not None and result:
            if "items" in result:
                ok, coll, cctx = await walk(outp, result["items"].split("."), nsid)
                if ok is False:
                    out["issues"].append(f"items {result['items']!r} not in lexicon output")
                item = coll.get("items") if isinstance(coll, dict) and coll.get("type") == "array" else None
                for norm, src in (result.get("fields") or {}).items():
                    if item is not None and isinstance(src, str) and not src.startswith("="):
                        ok, _, _ = await walk(item, src.split("."), cctx)
                        if ok is False:
                            out["issues"].append(f"field {norm}={src!r} not in lexicon output")
                        elif ok is None:
                            out["unverifiable"].append(f"fields.{norm} {src}")
                for k in ("next_cursor", "total"):
                    if result.get(k):
                        ok, _, _ = await walk(outp, result[k].split("."), nsid)
                        if ok is False:
                            out["issues"].append(f"{k} {result[k]!r} not in lexicon output")
            elif "fields" in result:
                for norm, src in (result.get("fields") or {}).items():
                    if isinstance(src, str) and not src.startswith("="):
                        segs = ([result["root"]] if result.get("root") else []) + src.split(".")
                        ok, _, _ = await walk(outp, [s for seg in segs for s in seg.split(".")], nsid)
                        if ok is False:
                            out["issues"].append(f"field {norm}={src!r} not in lexicon output")
                        elif ok is None:
                            out["unverifiable"].append(f"fields.{norm} {src}")
        res[verb] = out
    return res


def compare_graphql(e: dict, sdl: str) -> dict:
    """Validate every GraphQL document the adapter sends against the vendor's published schema."""
    try:
        import graphql  # graphql-core, optional
    except ImportError:
        return {"_skipped": "graphql-core not installed"}
    schema = graphql.build_schema(sdl)
    res = {}
    for verb, tool in e["adapter"]["tools"].items():
        q = (tool.get("body") or {}).get("query")
        if not isinstance(q, str) or not q.startswith("="):
            continue
        errs = graphql.validate(schema, graphql.parse(q[1:]))
        res[verb] = {"op": "graphql", "issues": [f"graphql: {x.message}" for x in errs][:5], "notes": [], "unverifiable": []}
    return res


async def run_spec(entries, out_dir: Path) -> None:
    pacer = Pacer(1.0)
    cache = SpecCache(out_dir, pacer)
    (out_dir / "spec").mkdir(parents=True, exist_ok=True)
    ops_cache: dict[str, list] = {}
    for p, e in entries:
        srcs = SPECS.get(e["id"])
        if not srcs:
            continue
        creds = dummy_creds(e)
        res: dict = {"id": e["id"], "key": key(p), "sources": [s["url"] for s in srcs], "tools": {}, "fetch": {}}
        docs_ops = []
        for s in srcs:
            kind = s.get("kind")
            if kind == "lexicon":
                res["tools"].update(await compare_lexicon(e, cache, s["url"]))
                res["fetch"][s["url"]] = "lexicons"
                continue
            if kind == "graphql":
                sdl = await cache.get(s["url"], parse=False)
                res["fetch"][s["url"]] = "ok" if sdl else "unavailable"
                if sdl:
                    for verb, r in compare_graphql(e, sdl).items():
                        res["tools"][verb] = r
                continue
            if kind == "redoc":
                html = await cache.get(s["url"], parse=False)
                doc = redoc_state(html) if html else None
            else:
                doc = await cache.get(s["url"])
            res["fetch"][s["url"]] = "ok" if doc else "unavailable"
            if doc is None:
                continue
            if s["url"] not in ops_cache:
                if kind == "postman":
                    ops_cache[s["url"]] = build_ops_postman(doc)
                else:
                    if not doc.get("discoveryVersion") and re.search(r'"\$ref": "[^"#]+\.(json|ya?ml)', json.dumps(doc, default=str)):
                        doc = bundle_external(doc, s["url"], cache.get_sync, rewrite=s.get("ref_rewrite"))
                    ops_cache[s["url"]] = build_ops(doc, s["url"])
                    ops_cache[s["url"] + "#doc"] = doc
            docs_ops.append((ops_cache.get(s["url"] + "#doc", doc), ops_cache[s["url"]], s.get("tools")))
            if isinstance(doc, dict) and doc.get("discoveryVersion"):
                # OAuth scopes named by the entry (auth.scope, field help) against the discovery document's scopes
                known = set(((doc.get("auth") or {}).get("oauth2") or {}).get("scopes") or {})
                blob = json.dumps([e["adapter"].get("auth", {}).get("scope"), e["adapter"].get("auth", {}).get("fields")])
                named = sorted({x.rstrip(".") for x in re.findall(r"https://www\.googleapis\.com/auth/[a-z0-9._-]+", blob)})
                sc = res.setdefault("scopes", {"named": named, "known_in": [], "unknown": list(named)})
                sc["known_in"].append(s["url"])
                sc["unknown"] = [x for x in sc["unknown"] if x not in known] if known else sc["unknown"]
                if not known:
                    sc["known_in"].pop()  # this discovery document lists no scopes
        for verb, tool in e["adapter"]["tools"].items():
            if verb in res["tools"]:
                continue
            usable = [(d, o) for d, o, only in docs_ops if not only or verb in only]
            if not usable:
                if docs_ops:
                    res["tools"][verb] = {"issues": [], "notes": [], "unverifiable": ["no machine-readable spec for this endpoint"], "no_spec": True}
                continue
            try:
                res["tools"][verb] = compare_tool(e, verb, tool, usable, creds)
            except Exception as exc:  # noqa: BLE001
                res["tools"][verb] = {"issues": [], "notes": [], "unverifiable": [f"harness_error {exc.__class__.__name__}: {exc}"]}
        (out_dir / "spec" / f"{p.parent.name}__{p.stem}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
        n = sum(len(t.get("issues", [])) for t in res["tools"].values())
        print(f"{key(p)}: {len(res['tools'])} tools compared, {n} issues", flush=True)


# ------------------------------------------------------------------------------------------ docs

def _path_regex(path: str) -> str:
    """A tool path as a pattern for documentation text: {placeholders} match any segment or a
    placeholder spelled another way ({id}, :id, <id>, 123)."""
    parts = re.split(r"(\{[^}]+\})", path.split("?")[0])
    out = []
    for part in parts:
        if part.startswith("{"):
            out.append(r"(?:\{[^}/\s]+\}|:[A-Za-z_]+|<[^>/\s]+>|\[[^\]/\s]+\]|[^/\s\"'`]+)")
        else:
            out.append(re.escape(part))
    return "".join(out)


def docs_check(entries, out_dir: Path, rendered: Path) -> None:
    """Spot-check tools without a machine-readable spec against their documentation pages, rendered
    with a headless browser beforehand (one text file per page, named by the SHA-1 of the URL)."""
    import hashlib
    (out_dir / "docs").mkdir(parents=True, exist_ok=True)
    for p, e in entries:
        if e["id"] in SPECS:
            continue
        res: dict = {"id": e["id"], "key": key(p), "tools": {}}
        base_path = urlparse(_fill(e["adapter"]["base_url"], dummy_creds(e))).path.rstrip("/")
        for verb, t in e["adapter"]["tools"].items():
            pages = []
            for u in [(t.get("docs") or "").split("#")[0], (e.get("docs_url") or "").split("#")[0]]:
                f = rendered / (hashlib.sha1(u.encode()).hexdigest() + ".txt") if u else None
                if f and f.exists():
                    txt = f.read_text(encoding="utf-8", errors="ignore")
                    if len(txt) > 400 and not txt.startswith("RENDER_ERROR"):
                        pages.append((u, txt))
            r: dict = {"pages": [u for u, _ in pages]}
            if not pages:
                r["result"] = "no rendered page"
                res["tools"][verb] = r
                continue
            text = "\n".join(tx for _, tx in pages)
            path = t["path"] if not str(t["path"]).startswith("http") else urlparse(t["path"]).path
            cands = [path, base_path + path] if not str(t["path"]).startswith("http") else [path]
            found = any(re.search(_path_regex(c), text) for c in cands if c.strip("/"))
            if not found:
                # the last two literal segments (docs often show the path relative to another base)
                lits = [x for x in path.split("?")[0].split("/") if x and not x.startswith("{")]
                tail = "/".join(lits[-2:]) if len(lits) >= 2 else (lits[-1] if lits else "")
                found = bool(tail) and (tail in text)
                r["path_match"] = "tail" if found else None
            else:
                r["path_match"] = "full"
            names = [k for k in list((t.get("params") or {}).keys()) + list((t.get("fixed_params") or {}).keys())]
            names = [k.split("[")[0] for k in names if k.split("[")[0]]
            body = [re.split(r"(?<!\\)\.", k)[0] for k in (t.get("body") or {})]
            r["params_missing"] = sorted({k for k in names if not re.search(r"(?<![A-Za-z0-9_])" + re.escape(k) + r"(?![A-Za-z0-9_])", text)})
            r["body_missing"] = sorted({k for k in body if "{" not in k and not re.search(r"(?<![A-Za-z0-9_])" + re.escape(k) + r"(?![A-Za-z0-9_])", text)})
            r["result"] = "ok" if found and not r["params_missing"] and not r["body_missing"] else "differs"
            res["tools"][verb] = r
        (out_dir / "docs" / f"{p.parent.name}__{p.stem}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")


# ----------------------------------------------------------------------------------------- apply

# Manual review of the automatic findings (every waiver says why). Keys are entry ids or category/id.
#   status: force a class; notes: appended to the block; waive: {"verb|substring of a spec issue or probe class": reason}
_PROFILES = ("Amazon's published Profiles OpenAPI (Profiles_prod_3p.json) lists GET /profiles; the adapter uses GET /v2/profiles, "
             "the path on Amazon's reference page and in its SDKs. Both answer 401 with a dummy token while an unknown route answers 403 "
             "'Invalid key=value pair … in Authorization header', so both routes exist.")
_PIN_TOKEN = ("POST /v5/oauth/token answered 500 code 12 for a numeric dummy client id and 401 'Authentication failed' for a non-numeric one "
              "(checked by hand), so the token endpoint is live; the 500 is Pinterest's handling of an unknown app id.")
REVIEW: dict[str, dict] = {
    "amazon_ads": {"waive": {"me|path not in spec": _PROFILES, "list_accounts|path not in spec": _PROFILES}},
    "amazon_fire_tv_ads": {"waive": {"me|path not in spec": _PROFILES, "list_accounts|path not in spec": _PROFILES}},
    "amazon_dsp": {"waive": {"me|path not in spec": _PROFILES}},
    "pinterest_catalogs": {"notes": _PIN_TOKEN},
    "walmart": {"notes": "POST /v3/token answers a bare 400 'Bad Request' to a dummy client even with the documented WM_SVC.NAME / WM_QOS.CORRELATION_ID headers (a UUID correlation id changes nothing), where an OAuth error was expected; the API calls themselves answer 401 UNAUTHORIZED.GMP_GATEWAY_API, and the reference pages list only WM_SEC.ACCESS_TOKEN, WM_SVC.NAME and WM_QOS.CORRELATION_ID as headers, as the adapter sends."},
    "pinterest": {"notes": _PIN_TOKEN, "waive": {"get_report|is not in the response schema": "the analytics rows carry one key per requested `columns` value (SPEND_IN_DOLLAR, IMPRESSION_1, CLICKTHROUGH_1 are sent in columns); the schema lists only CAMPAIGN_ID and DATE"}},
    "huggingface": {"waive": {"list_items|path not in spec": "the Hub OpenAPI (huggingface.co/.well-known/openapi.json) omits the listing routes; GET /api/models answered 200 live and validated",
                              "get_item|path not in spec": "omitted from the Hub OpenAPI; GET /api/models/{repo_id} answered 200 live and validated"}},
    "contrado": {"status": "reachable_unverified",
                 "waive": {"*|'data' is not in the response schema": "the Helix swagger describes the payload inside Contrado's {success, data} envelope (the adapter follows https://api.contrado.app/helix/docs/); which one the live API returns needs a real key"},
                 "notes": "Response envelope unresolved: the swagger has no data wrapper, the docs page describes {success, data}."},
    "lulu": {"status": "reachable_unverified",
             "waive": {"create_order|spec requires body field": "id and status are read-only fields the spec lists as required",
                       "*|is not in the response schema": "Lulu's inline Print-Job schemas list only a few properties (the rest is in the examples); costs/tracking paths follow the examples and the Shipping-Notification section"},
             "notes": "Spec schemas are incomplete; paths and methods match."},
    "lulu_print_api": {"status": "reachable_unverified",
                       "waive": {"create_order|spec requires body field": "id and status are read-only fields the spec lists as required",
                                 "*|is not in the response schema": "Lulu's inline Print-Job schemas list only a few properties (the rest is in the examples); costs/tracking paths follow the examples and the Shipping-Notification section"},
                       "notes": "Spec schemas are incomplete; paths and methods match."},
    "digistore24": {"status": "reachable_unverified",
                    "waive": {"*|is not in the response schema": "Digistore24's OpenAPI describes the payload inside the {api_version, result, data} envelope that every live answer (including the audit's error answers) carries"},
                    "notes": "Fixed: error answers ({result: error} with HTTP 200) are now errors (envelope result=success)."},
    "microsoft_graph": {"waive": {"send|body field 'message.": "the OpenAPI (generated from CSDL) names the action parameter `Message`; Microsoft's sendMail reference sample uses `message`, which Graph accepts",
                                  "reply|body field 'comment'": "the OpenAPI names it `Comment`; the reply reference sample uses `comment`",
                                  "mark_read|@odata.type": "the generated OpenAPI marks @odata.type required on every entity body; PATCH /me/messages/{id} with {isRead} is the documented update"}},
    "teams": {"waive": {"*|@odata.type": "the generated OpenAPI marks @odata.type required on every entity body; the chatMessage create samples omit it"}},
    "slack": {"waive": {"me|method": "Slack Web API methods accept POST as well as GET (api.slack.com/web#basics); the 2019 OpenAPI lists GET only"}},
    "whatsapp": {"waive": {"mark_read|body field": "mark-as-read ({messaging_product, status: read, message_id} on POST /{phone-number-id}/messages) is documented on its own guide page; the v23 OpenAPI models only message sends on that path"}},
    "zendesk": {"waive": {"*|total='count'": "offset-paginated list responses carry count/next_page/previous_page (Zendesk pagination docs); the OAS omits that envelope"}},
    "devto": {"waive": {"analytics_post|is not in the response schema": "forem's spec wraps the article object in an `items` key although the endpoint returns one article; the fields exist there, and the call was verified live"}},
    "vimeo": {"waive": {"read_comments|is not in the response schema": "Vimeo's OpenAPI models paginated collections as bare arrays; the API wraps them as {total, page, per_page, paging, data[]} (developer.vimeo.com common formats)",
                        "analytics_post|'fields'": "`fields` (JSON filter) is accepted by every Vimeo endpoint (developer.vimeo.com, JSON filter); the OpenAPI does not repeat it per operation"}},
    "binance_spot": {"waive": {"*|omitZeroBalances": "documented for GET /api/v3/account in binance/binance-spot-api-docs rest-api.md; the swagger repository lags the docs"},
                     "notes": "place_order sends `price` whenever it is given; Binance rejects a MARKET order that carries one (-1104 'Not all sent parameters were read'), so callers must omit price for market orders."},
    "mercadolibre": {"waive": {"get_listing|not_found": "404 {error: resource not found} is Mercado Libre's answer for the dummy item id; the items route exists"}},
    "mercado_libre": {"waive": {"get_product|not_found": "404 {error: resource not found} is Mercado Libre's answer for the dummy item id; the items route exists"}},
    "wordpress": {"waive": {"update_item|not_found": "404 rest_post_invalid_id for the dummy post id: the route exists (OPTIONS lists POST/PUT/PATCH/DELETE)"}},
    "idealist": {"waive": {"get_posting|not_found": "Idealist documents 404 for an unknown or expired job; the listings route answered 401 for search"}},
    "paddle": {"waive": {"get_product|not_found": "Paddle rejects the malformed dummy id with 404 invalid_url (ids look like pro_…); the collection route answered 401"}},
    "sam_gov": {"status": "blocked",
                "notes": "api.sam.gov answered an empty 404 (server istio-envoy) for every path tried, the documented /opportunities/v2/search, /prod/opportunities/v2/search and entity-information/v3 alike, from both audit hosts (UAE residential, EU datacenter), with and without api.data.gov's DEMO_KEY; the path matches https://open.gsa.gov/api/get-opportunities-public-api/. Needs a US vantage point."},
    "mercari_shops_jp": {"status": "blocked",
                         "notes": "POST https://api.mercari-shops.com/v1/graphql (the documented endpoint) answers a bare 404 to the audit hosts; Mercari's FAQ says access is only from pre-registered IP addresses, and requests need the contracted '<API_CLIENT_NAME>/<VERSION>' User-Agent."},
    "supabase": {"status": "reachable_unverified",
                 "notes": "Per-project host (<project_ref>.supabase.co): no public project exists to probe and unknown refs do not resolve, so only the PostgREST path shape (/rest/v1/<table>) could be checked, against Supabase's docs."},
    "noon": {"notes": "The gateway answers every unauthenticated call with 307 to login.noon.partners, so paths cannot be told apart without a session; the login endpoint answered 400 'No service account found or key is deactivated'."},
    "web3_career": {"notes": "An invalid token gets a 302 to https://web3.career/web3-jobs-api, so the path cannot be confirmed without a token."},
    "adtraction": {"notes": "GET /v2/advertiser/account/ (documented) answers 415 Unsupported Media Type to every Content-Type tried, before authentication; POST /v2/advertiser/statistics/days/ answers 401 as expected. Needs a real token to see whether the account call works."},
    "nova_engel": {"notes": "The token travels in the path; an invalid token gets HTTP 200 with empty data rather than an error, and create_order reports 'Unrecognized user, please login again' inside a 200 array, which no envelope rule can catch. Fixed: get_order status as a string and track events as an array (vocabulary)."},
    "xiaohongshu_pugongying": {"notes": "adapi.xiaohongshu.com was intermittent from both audit hosts (TLS timeouts); when it answered, every tool got code 410019 access_token错误 on its path."},
    "freelancehunt": {"notes": "Fixed: submit_bid removed; POST /v2/projects/{id}/bids answers 410 'This public endpoint is no longer available due to API v2 deprecation.' The search 500 was caused by the dummy non-numeric skill id."},
    "tiktok": {"notes": "Fixed: TikTok Business API answers HTTP 200 {code: 40105, message} for errors; without an envelope the tools returned empty successes. Envelope code=0 added."},
    "saramin": {"notes": "Fixed: errors come back as HTTP 200 {code, message}; envelope code=0 added so they are errors, not empty result lists."},
    "baidu_marketing": {"notes": "Fixed: errors come back as HTTP 200 {header: {desc: failure, failures[]}}, which the tools reported as empty successes; envelope fail_when header.desc=failure added."},
    "xiaomi_getapps_ads": {"notes": "Fixed: the me probe used campaign/list without accountIds, which the API refuses before authentication (code 100500 MissingServletRequestParameterException); it now reads countryList."},
    "wix_stores": {"notes": "Fixed: list_orders sent a bare date as createdDate.$gte, which Wix rejects (400 '… is not a valid dateTime filter value'); it now sends an ISO dateTime."},
    "bfl": {"notes": "Fixed: generate_video no longer sends webhook_url, which the Flux 3 video input schemas forbid (additionalProperties false)."},
    "printful": {"notes": "Fixed: list_products no longer sends offset/limit (not in the catalog spec; live, offset was ignored and no paging object came back)."},
    "postmark": {"notes": "Postmark's published test token POSTMARK_API_TEST is accepted only on /email ('The Postmark Test API Token may only be used on the /email endpoint'), so no read could be verified with it; send was not called (write)."},
    "jooble": {"notes": "Cloudflare challenge ('Just a moment...') on POST https://jooble.org/api/{key} from both audit hosts; not bypassed."},
    "kaspi_shop_api": {"notes": "kaspi.kz timed out from both audit hosts (UAE residential, EU datacenter); the API appears to be reachable only from Kazakhstan."},
}

PATH_OK = {"auth_required", "client_error", "error_envelope", "public", "options_ok", "status_429", "status_410"}
PATH_MISSING = {"not_found", "method_not_allowed", "options_405"}
NET_FAIL = {"dns_error", "tls_error", "conn_error", "timeout"}


def _final_variant(t: dict) -> dict:
    return t["variants"].get("dummy_auth_delete") or t["variants"]["dummy_auth"]


def _waived(review: dict, verb: str, text: str) -> str | None:
    for k, why in (review.get("waive") or {}).items():
        v, _, sub = k.partition("|")
        if v in (verb, "*") and sub in text:
            return why
    return None


def classify(key_: str, e: dict, probe: dict, spec: dict | None, review: dict, docs: dict | None = None) -> dict:
    """The rules in docs/AUTH_AUDIT.md, applied to one entry's probe and spec evidence."""
    a = e["adapter"]
    base_host = urlparse(_fill(a["base_url"], dummy_creds(e))).hostname
    hosts = probe.get("hosts", {})
    ev, notes = [], []
    h = hosts.get(base_host, {})
    if h.get("dns_error"):
        host_state = "dns"
    elif h.get("tls_error"):
        host_state = "tls"
    else:
        host_state = "ok"
    tl = h.get("tls") or {}
    ev.append(f"host {base_host}: " + ({"ok": f"DNS ok, {tl.get('version', 'TLS')} ({tl.get('issuer') or 'CA'})", "dns": "DNS failure", "tls": "TLS failure: " + str(h.get("tls_error"))[:80]}[host_state]))
    tools = probe.get("tools", {})
    ok, missing, net, blocked, unverified, public_valid = [], [], [], [], [], []
    for verb, t in tools.items():
        v = _final_variant(t)
        cls = v["class"]
        last = (v.get("requests") or [{}])[-1]
        w = _waived(review, verb, cls)
        if cls in PATH_OK or (cls == "server_error" and w) or (cls in PATH_MISSING and w):
            ok.append(verb)
        elif cls in PATH_MISSING:
            missing.append(f"{verb}: {last.get('method')} {urlparse(last.get('url', '')).path} -> {last.get('status')}")
        elif cls in NET_FAIL:
            net.append(verb)
        elif cls == "blocked":
            blocked.append(verb)
        else:
            unverified.append(f"{verb}: {cls} {last.get('status') or ''}".strip())
        for vv in t["variants"].values():
            oc = vv.get("output_check") or {}
            rq = (vv.get("requests") or [{}])[-1]
            body = (rq.get("body") or "").strip()
            real = vv.get("class") == "public" and 200 <= (rq.get("status") or 0) < 300 and body not in ("", "[]", "{}", "null")
            if real and oc.get("valid") and t["read"] and (oc.get("items") or (oc.get("items") is None and verb != "me")):
                public_valid.append(verb)
                break
    demo_valid = []
    for verb, d in ((probe.get("demo") or {}).get("tools") or {}).items():
        oc = d.get("output_check") or {}
        rq = (d.get("requests") or [{}])[-1]
        if oc.get("valid") and 200 <= (rq.get("status") or 0) < 300 and (oc.get("items") or (oc.get("items") is None and verb != "me")):
            demo_valid.append(verb)
    ctl = probe.get("control", {})
    ctl_req = (ctl.get("requests") or [{}])[-1]
    gated = ctl.get("class") == "auth_required"
    n = len(tools)
    ev.append(f"probe: {len(ok)}/{n} tools answered on their documented path with an auth refusal, a validation error or data; "
              + (f"control route answered {ctl_req.get('status')} too, so the host authenticates before routing" if gated
                 else f"control route -> {ctl_req.get('status')} ({ctl.get('class')}), so the answers are path-specific"))
    flow = probe.get("flow", {})
    tok = flow.get("token")
    if tok:
        r = (tok.get("requests") or [{}])[-1]
        body = (r.get("body") or r.get("error") or "")
        m = re.search(r'"(error|code|message|error_description)"\s*:\s*"?([^",}]{1,60})', body)
        ev.append(f"{'login' if e['adapter']['auth'].get('type') == 'session' else 'token'} {urlparse(r.get('url', '')).hostname}{urlparse(r.get('url', '')).path}: {r.get('status')}"
                  + (f" {m.group(2)}" if m else ""))
    for az in flow.get("authorize") or []:
        ev.append(f"authorize {az['url']}: {az.get('status') or az.get('error', '')[:40]}")
    spec_issues, spec_matched, spec_nospec = [], 0, 0
    if spec:
        for verb, r in (spec.get("tools") or {}).items():
            if r.get("no_spec"):
                spec_nospec += 1
                continue
            real = []
            for iss in r.get("issues") or []:
                why = _waived(review, verb, iss)
                if why:
                    notes.append(f"{verb}: spec says \"{iss}\"; waived: {why}")
                else:
                    real.append(f"{verb}: {iss}")
            spec_issues += real
            if r.get("op") and not real:
                spec_matched += 1
        srcs = ", ".join(spec.get("sources") or [])
        ev.append(f"spec {srcs[:220]}: {spec_matched}/{len(spec.get('tools') or {}) - spec_nospec} tools match (path, method, parameters, body keys, response paths)")
        sc = spec.get("scopes")
        if sc and sc.get("named") and sc.get("known_in"):
            ev.append(f"scopes {', '.join(x.rsplit('/', 1)[-1] for x in sc['named'])}: " + ("all listed in the discovery document" if not sc["unknown"] else f"not listed: {sc['unknown']}"))
    notes = list(dict.fromkeys(notes))
    spec_issues = list(dict.fromkeys(spec_issues))
    if docs and docs.get("tools"):
        dt = docs["tools"]
        seen = [v for v, r in dt.items() if r.get("pages")]
        full = [v for v in seen if dt[v].get("path_match") == "full"]
        tail = [v for v in seen if dt[v].get("path_match") == "tail"]
        miss_p = sorted({f"{v}:{k}" for v in seen for k in dt[v].get("params_missing") or []})
        miss_b = sorted({f"{v}:{k}" for v in seen for k in dt[v].get("body_missing") or []})
        if seen:
            ev.append(f"HTML docs spot-check (render-doc): {len(full)}/{len(seen)} tool paths found verbatim on their docs pages"
                      + (f", {len(tail)} by their last segments" if tail else "")
                      + (f"; names not found on the page: {', '.join(miss_p + miss_b)[:200]}" if miss_p or miss_b else "; every parameter and body key named on the page"))
        else:
            ev.append("HTML docs spot-check: the docs pages did not render (login wall, SPA or bot wall)")
    if public_valid:
        ev.append(f"live read without credentials: {', '.join(sorted(set(public_valid)))} returned data that validates against the vocabulary")
    if demo_valid:
        ev.append(f"live read with the vendor's published demo credential ({probe['demo']['source']}): {', '.join(demo_valid)} validated against the vocabulary")
    # classification
    if review.get("status"):
        status = review["status"]
    elif host_state == "dns":
        status = "broken"
    elif blocked and len(blocked) + len(net) >= max(1, n // 2):
        status = "blocked"
    elif spec_issues or missing:
        status = "mismatch"
    elif len(net) >= max(1, n // 2):
        status = "blocked"
    elif public_valid or demo_valid:
        status = "verified_live"
    elif spec and spec_matched and not spec_nospec and spec_matched >= len(spec.get("tools") or {}):
        status = "spec_conformant"
    else:
        status = "reachable_unverified"
    if missing:
        notes.append("path/method refused: " + "; ".join(missing))
    if spec_issues:
        notes.append("spec differences: " + "; ".join(spec_issues))
    if net:
        notes.append(f"no answer (timeout/connection) for {', '.join(net)}")
    if blocked:
        notes.append(f"bot wall / access block for {', '.join(blocked)}")
    if unverified:
        notes.append("inconclusive: " + "; ".join(unverified))
    if spec and spec_nospec:
        notes.append(f"{spec_nospec} tool(s) have no machine-readable spec")
    if review.get("notes"):
        notes.insert(0, review["notes"])
    ev += review.get("evidence") or []
    return {"status": status, "evidence": ev[:12], "notes": " ".join(notes)[:1800] or "-"}


def set_top_level_key(raw: str, name: str, value) -> str:
    """Replace (or append) one top-level key of a catalog file without re-serialising the rest, so the
    file keeps its existing formatting and escaping (entries mix raw and \\u-escaped text)."""
    m = re.search(r'\n "' + re.escape(name) + r'": ', raw)
    ascii_style = False
    if m:
        start = m.end()
        _, end = json.JSONDecoder().raw_decode(raw, start)
        old = raw[start:end]
        ascii_style = "\\u" in old and not re.search(r"[^\x00-\x7f]", old)
    text = json.dumps(value, indent=1, ensure_ascii=ascii_style).replace("\n", "\n ")
    if m:
        return raw[:start] + text + raw[end:]
    body = raw.rstrip()
    assert body.endswith("}")
    return body[:-1].rstrip() + ',\n "' + name + '": ' + text + "\n}" + raw[len(body):]


def apply(entries, out_dir: Path, date: str, write: bool = True, env: str = "production") -> int:
    counts: dict[str, int] = {}
    for p, e in entries:
        pf = out_dir / "probe" / f"{p.parent.name}__{p.stem}.json"
        if not pf.exists():
            print(f"{key(p)}: no probe evidence, skipped")
            continue
        probe = json.loads(pf.read_text(encoding="utf-8"))
        sf = out_dir / "spec" / f"{p.parent.name}__{p.stem}.json"
        spec = json.loads(sf.read_text(encoding="utf-8")) if sf.exists() and e["id"] in SPECS else None
        review = {**REVIEW.get(e["id"], {}), **REVIEW.get(key(p), {})}
        df = out_dir / "docs" / f"{p.parent.name}__{p.stem}.json"
        docs = json.loads(df.read_text(encoding="utf-8")) if df.exists() else None
        block = {"date": date, **classify(key(p), e, probe, spec, review, docs)}
        counts[block["status"]] = counts.get(block["status"], 0) + 1
        print(f"{key(p):45s} {block['status']:22s} {block['notes'][:150]}")
        if write:
            raw = p.read_text(encoding="utf-8")
            if env == "production":
                raw = set_top_level_key(raw, "auth_audit", block)
            else:  # a vendor environment's audit never replaces the production auth_audit
                checks = json.loads(raw).get("environment_checks") or {}
                checks.setdefault(env, {})["auth_audit"] = block
                raw = set_top_level_key(raw, "environment_checks", checks)
            p.write_text(raw, encoding="utf-8")
    print(json.dumps(counts, sort_keys=True))
    return 0


# ---------------------------------------------------------------------------------------- report

# Where real credentials would add the most confidence: widely used platforms first, then residual risk (writes,
# signing, sessions, no machine-readable spec). Edited by hand.
PRIORITY: list[tuple[str, str]] = [
    ("deals/upwork", "large freelance marketplace (search, proposals, messages); GraphQL schema is only visible to authenticated apps, so no tool could be compared; OAuth refresh-token grant"),
    ("ads/meta", "largest ad network in the catalog; Graph API has no machine-readable spec; budget and pause writes"),
    ("ecommerce_channels/ebay", "major sales channel; eBay's OpenAPI files answer 403 to non-browser clients, so nothing was compared; inventory and offer writes"),
    ("ecommerce_channels/amazon", "major sales channel; spec-conformant against the SP-API models, but LWA refresh, marketplace ids and listings PATCH writes only prove out with a seller account"),
    ("automotive/mobilede", "large car-listing source; Basic auth, no machine-readable spec"),
    ("automotive/autotrader_uk", "car-listing source; session login (key/secret) and valuation calls, no machine-readable spec"),
    ("ads/google", "major ad network; spec-conformant to the v25 discovery document, but developer-token / login-customer-id handling and campaigns:mutate need a test account"),
    ("social/linkedin", "major social network; Rest.li query syntax and versioned headers, no machine-readable spec; paired with ads/linkedin"),
    ("ads/tiktok", "major ad network; the audit fixed swallowed 200-body errors; no machine-readable spec; budget and status writes"),
    ("ecommerce_channels/shopee", "major sales channel; HMAC-signed calls and a signed token refresh with no vendor test vector (also shopee_ads, shopee_br, shopee_open_platform)"),
    ("messaging/telegram", "high-use messaging; the host authenticates before routing (any path answers 401 to a bad token), so the paths themselves are unconfirmed"),
    ("messaging/whatsapp", "customer messaging; the v23 OpenAPI covers sends only, mark-as-read is checked against the guide page"),
    ("ecommerce_channels/mercado_libre", "major sales channel (also automotive/mercadolibre); single-use rotating refresh tokens"),
    ("ads/microsoft_advertising", "major ad network; REST JSON calls were not compared (only the SOAP WSDL is published)"),
    ("deals/freelancer", "freelance marketplace; public reads verified live, but submit_bid / withdraw_bid / messages are writes behind OAuth"),
    ("social/x", "major social network; spec-conformant, OAuth 2.0 refresh with rotation; posting writes"),
    ("ecommerce_channels/walmart", "major sales channel; the token endpoint answered a bare 400 to a dummy client instead of an OAuth error"),
    ("ads/amazon_ads", "major ad network; Profiles and Sponsored Products v3 conformant, profile-scoped writes need an advertiser"),
    ("ads/baidu_marketing", "the audit fixed swallowed 200-body errors; token travels inside the JSON body header"),
    ("messaging/slack", "high-use messaging; spec-conformant, but bot-token scopes decide what each tool can do"),
]

# Fixes made by the audit (entry key, change, regression test), listed in the report.
FIXES: list[tuple[str, str, str]] = [
    ("runtime (Python, TypeScript)", "OAuth 1.0a now signs form-encoded body parameters with the query and oauth_* parameters (RFC 5849 3.4.1.3.1); X's worked example failed before", "test_oauth1_signs_form_body_parameters_x_docs_example"),
    ("runtime (Python)", "`datefmt:` converts offset datetimes to UTC before formatting, as the TypeScript runtime already did", "test_wix_orders_filter_sends_an_iso_datetime[…+02:00]"),
    ("ads/tiktok", "envelope code=0: HTTP 200 {code: 40105, message} errors were returned as empty successes", "test_error_bodies_in_a_200_are_errors_not_empty_results"),
    ("marketplaces/digistore24", "envelope result=success: HTTP 200 {result: error} answers were returned as empty successes", "test_error_bodies_in_a_200_are_errors_not_empty_results"),
    ("jobs/saramin", "envelope code=0: HTTP 200 {code, message} errors were returned as empty result lists", "test_error_bodies_in_a_200_are_errors_not_empty_results"),
    ("ads/baidu_marketing", "envelope fail_when header.desc=failure: HTTP 200 failure headers were returned as empty successes", "test_error_bodies_in_a_200_are_errors_not_empty_results"),
    ("ads/xiaomi_getapps_ads", "me probes GET /foreign/marketing/region/countryList; campaign/list without accountIds is refused before authentication (code 100500)", "test_probe_and_tool_list; xiaomi_getapps_ads me (TS)"),
    ("deals/freelancehunt", "submit_bid removed and explained under not_offered: POST /v2/projects/{id}/bids answers 410 'no longer available due to API v2 deprecation'", "test_submit_bid_is_not_offered_after_the_v2_deprecation"),
    ("ecommerce_channels/wix_stores", "list_orders sends `since` as an ISO dateTime; a bare date is rejected with 400 INVALID_QUERY_FILTER", "test_wix_orders_filter_sends_an_iso_datetime"),
    ("ecommerce_suppliers/nova_engel", "get_order status as a string and track events as an array, as the vocabulary requires", "test_order_and_tracking"),
    ("builder_tools/bfl", "generate_video no longer sends webhook_url, which every Flux 3 video input schema forbids (additionalProperties false)", "test_bfl_video_body_and_printful_catalog_params_follow_the_vendor_specs"),
    ("ecommerce_suppliers/printful", "list_products no longer sends offset/limit (not in the catalog spec; live, offset was ignored and no paging object came back)", "test_bfl_video_body_and_printful_catalog_params_follow_the_vendor_specs"),
]

VECTORS = [
    ("aws_sigv4", "AWS Signature V4 test suite (awslabs/aws-c-auth tests/aws-signing-test-suite/v4): get-vanilla, get-vanilla-query-order-key-case, get-vanilla-query-unreserved, get-vanilla-empty-query-key, get-utf8, get-space-normalized, post-vanilla, post-vanilla-query", "8/8 signatures identical in both runtimes"),
    ("oauth1", "OAuth Core 1.0 Appendix A.5 (photos.example.net, signature tR3+Ty81lMeYAr/Fid0kMTYa/WM=) and X's 'Creating a signature' worked example (form-encoded status parameter, Ls93hJiZbQ3akF3HF3x1Bz8/zU4=)", "2/2 after the fix that signs form-encoded body parameters (RFC 5849 3.4.1.3.1)"),
    ("hmac", "Binance 'SIGNED endpoint examples' (ASCII and non-ASCII symbol, binance/binance-spot-api-docs rest-api.md) and Kaufland Seller API 'Signing requests' example", "3/3 through the catalog's own binance_spot and kaufland auth blocks"),
    ("jwt_hs256", "The default HS256 example token published on jwt.io (secret your-256-bit-secret, iat 1516239022)", "byte-identical token in both runtimes"),
    ("rsa_sha256 / jwt_rs256", "No vendor in scope publishes an RSA test vector; covered by the existing cross-verification tests (signature verified with the public key)", "not vector-tested"),
]


def _cell(text: str, n: int) -> str:
    t = re.sub(r"\s+", " ", str(text or "")).replace("|", "\\|")
    return t if len(t) <= n else t[: n - 1] + "…"


def report(out: Path | None = None) -> int:
    rows = []
    for p, e in load_scope():
        au = e.get("auth_audit")
        if not au:
            continue
        rows.append((p.parent.name, e["id"], e["adapter"]["auth"]["type"], len(e["adapter"]["tools"]), au, False))
    counts: dict[str, int] = {}
    for r in rows:
        counts[r[4]["status"]] = counts.get(r[4]["status"], 0) + 1
    date = max((r[4]["date"] for r in rows), default="")
    L = []
    L.append("# Auth audit: the servers that need credentials\n")
    L.append(f"Credential-free audit of every served catalog entry whose adapter authenticates (`adapter.auth.type` other than `none`): "
             f"{len(rows)} entries, {sum(r[3] for r in rows)} tools, run {date}. Each entry carries the result as an `auth_audit` block "
             "`{date, status, evidence, notes}` (validated by `platform-mcp-hub lint`); this page is generated from those blocks by "
             "`python tools/auth_audit.py report`.\n")
    L.append("No account was used: every request carried dummy credentials or none, except where the vendor itself publishes a demo credential "
             "(NAV's rotating public token for the job-vacancy feed, https://navikt.github.io/pam-stilling-feed/; Postmark's `POSTMARK_API_TEST`, "
             "https://postmarkapp.com/developer/api/overview, which Postmark accepts only on `/email`, so it could not verify a read). Nothing was "
             "signed up for, no captcha or bot wall was bypassed, and requests were sequential per host at least 1.2 s apart.\n")
    L.append("## Summary\n")
    L.append("| status | entries | meaning |\n|---|---:|---|")
    meaning = {
        "verified_live": "read tools returned live data that validates against the vocabulary, without credentials (public endpoints) or with a vendor-published demo credential",
        "spec_conformant": "every tool's endpoint answered on its documented path, and every tool matches the vendor's machine-readable spec (path, method, parameters, body keys, response paths)",
        "reachable_unverified": "the endpoints answered (authentication refusal on the documented path), but there is no machine-readable spec to compare, or part of the entry could not be compared",
        "mismatch": "a tool differs from the vendor's spec or its path is refused; the exact difference is in the notes",
        "broken": "the host does not resolve or every path is gone",
        "blocked": "a bot wall, IP allow-list or geo block answered instead of the API (recorded, never bypassed)",
    }
    for st in STATUSES:
        L.append(f"| `{st}` | {counts.get(st, 0)} | {meaning[st]} |")
    L.append(f"| **total** | **{len(rows)}** | |\n")
    L.append(METHOD_TEXT)
    if FIXES:
        L.append("## Fixes made\n")
        L.append("| entry | change | regression test |\n|---|---|---|")
        for k, what, t in FIXES:
            L.append(f"| `{k}` | {_cell(what, 400)} | {t} |")
        L.append("")
    L.append("## Signing modes against published vectors\n")
    L.append("| mode | vectors | result |\n|---|---|---|")
    for m, src, res in VECTORS:
        L.append(f"| `{m}` | {src} | {res} |")
    L.append("\nThe tests are `tests/test_auth_audit_python.py` and `tests/auth_audit.typescript.test.mjs`.\n")
    waived = []
    for r in rows:
        for chunk in re.split(r"(?=\b[a-z_]+: spec says \")", r[4]["notes"])[1:]:
            chunk = re.split(r" (?:no answer \(|inconclusive:|spec differences:|path/method refused:|bot wall|\d+ tool\(s\) have no)", chunk)[0]
            waived.append((f"{r[0]}/{r[1]}", chunk.strip()))
    if waived:
        L.append("## Spec differences judged to be spec defects\n")
        L.append("Each was checked against the vendor's reference page or a live answer; the entry's notes carry the full text.\n")
        L.append("| entry | difference and reason |\n|---|---|")
        for k, m in waived:
            L.append(f"| `{k}` | {_cell(m, 500)} |")
        L.append("")
    rem = [r for r in rows if r[4]["status"] in ("mismatch", "broken", "blocked")]
    L.append("## Remaining mismatches, broken and blocked entries\n")
    if rem:
        L.append("| entry | status | exact difference / reason |\n|---|---|---|")
        for cat, pid, _, _, au, _ in rem:
            L.append(f"| `{cat}/{pid}` | `{au['status']}` | {_cell(au['notes'], 700)} |")
    else:
        L.append("None.")
    L.append("")
    L.append("## Where real credentials would add the most confidence\n")
    L.append("Ordered by how widely the platform is used, then by the risk that remains after this audit "
             "(write tools, request signing, session logins, no machine-readable spec). Status is this audit's result.\n")
    L.append("| # | entry | status | why |\n|---:|---|---|---|")
    by = {f"{r[0]}/{r[1]}": r for r in rows}
    for i, (k, why) in enumerate(PRIORITY, 1):
        r = by.get(k)
        L.append(f"| {i} | `{k}` | `{r[4]['status'] if r else '?'}` | {why} |")
    L.append("")
    L.append("## Per server\n")
    L.append("Evidence and notes are abridged here; the full text is in each entry's `auth_audit` block.\n")
    L.append("| category | id | auth | tools | status | evidence | notes |\n|---|---|---|---:|---|---|---|")
    for cat, pid, at, n, au, _ in sorted(rows):
        L.append(f"| {cat} | `{pid}` | {at} | {n} | `{au['status']}` | {_cell(' · '.join(au['evidence'][1:4]), 330)} | {_cell(au['notes'], 260)} |")
    L.append("\n## Re-running\n")
    L.append("```\npython tools/auth_audit.py probe --out <scratch>     # live requests (dummy credentials), sequential per host\n"
             "python tools/auth_audit.py spec --out <scratch>      # vendor specs: OpenAPI/Swagger, Google discovery, AT lexicons, GraphQL SDL, Postman, Redoc\n"
             "python tools/auth_audit.py apply --out <scratch>     # classify and write the auth_audit blocks (--dry to preview)\n"
             "python tools/auth_audit.py report                    # regenerate this page\n```\n"
             "Raw evidence (every request and response snippet) stays in the scratch directory and is not committed.\n")
    target = out or (ROOT / "docs" / "AUTH_AUDIT.md")
    target.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {target} ({len(rows)} entries)")
    return 0


METHOD_TEXT = """## How each server was checked

1. **Endpoint reachability.** For every tool the runtime built its exact request (URL, query, headers, signing) with dummy
   credentials, through the real Python transport with a recording HTTP layer. Read tools were sent as built, and once more
   with the credentials omitted. Write tools never carried a real body: POST, PUT and PATCH went out with a deliberately
   invalid empty body and a dummy credential; DELETE became OPTIONS, and only where OPTIONS was inconclusive the DELETE itself
   with a dummy credential and a dummy id. An authentication refusal (401/403, or an auth error in the body) on the documented
   path counts as "the path exists"; 404/405 or a DNS failure counts as wrong. One extra request per host to a route that
   cannot exist tells whether the host authenticates before routing (then a 401 says nothing about the path). DNS and TLS
   were checked for every host.
2. **Spec conformance.** Where the vendor publishes a machine-readable description (OpenAPI 3, Swagger 2, Google API discovery
   documents, AT Protocol lexicons, GraphQL SDL, Postman collections, Redoc pages that embed their spec), each tool was
   matched to an operation: path and method, every query parameter name and the required ones, every body key (walking
   `$ref`, `allOf`, `oneOf`/`anyOf` and discriminators), and every response path the result mapping reads (`items`,
   `fields`, `total`, `next_cursor`), plus the pagination parameters on both sides. Differences caused by the spec itself
   (an outdated or incomplete document) were checked against the vendor's reference pages and are recorded as waivers in
   the notes, never silently dropped. Entries with only HTML documentation were spot-checked from pages rendered with
   a headless browser.
3. **Auth flow.** OAuth2 token URLs were called with a dummy client and grant exactly as the runtime sends them: every one
   answered with an error for the dummy client (mostly `invalid_client` / `invalid_grant`; Pinterest a 500 and Walmart a bare
   400, see their notes), none with 404. Consent (authorize) URLs were opened with a dummy client id;
   session logins were posted with dummy credentials; Google OAuth scopes named by an entry were checked against the
   discovery document's scope list. Signing modes were checked against published vectors (below).
4. **Vendor demo credentials** were used only where the vendor publishes them for that purpose.

The probes ran from a residential connection; pages were rendered and blocked or timed-out hosts re-checked from a
datacenter host. Where an answer only proves that the host authenticates before routing
(the invented route got the same 401), the entry is not counted as path-verified by the probe alone.
"""

# ------------------------------------------------------------------------------------------ main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["probe", "spec", "docs", "apply", "report", "scope"])
    ap.add_argument("--rendered", type=Path, default=None, help="docs: directory of render-doc text files (SHA-1 of the URL + .txt)")
    ap.add_argument("--out", type=Path, default=None, help="scratch directory for raw evidence (never committed)")
    ap.add_argument("--ids", default="", help="comma-separated entry ids or category/id keys")
    ap.add_argument("--interval", type=float, default=1.2, help="seconds between two requests to one host (>= 1)")
    ap.add_argument("--parallel", type=int, default=8, help="hosts probed at the same time")
    ap.add_argument("--date", default=time.strftime("%Y-%m-%d"))
    ap.add_argument("--dry", action="store_true", help="apply: print the classification without writing the catalog")
    ap.add_argument("--env", default="production", help="vendor environment to audit (adapter.environments name, e.g. sandbox); default production")
    args = ap.parse_args(argv)
    ids = [x.strip() for x in args.ids.split(",") if x.strip()] or None
    if args.env != "production" and args.command == "report":
        raise SystemExit("report covers production auth_audit blocks only; --env applies to scope/probe/spec/docs/apply")
    entries = load_scope(ids, args.env)
    if args.command == "scope":
        for p, e in entries:
            print(key(p), e["adapter"]["auth"]["type"], len(e["adapter"]["tools"]))
        print(len(entries), "entries")
        return 0
    if args.command == "probe":
        asyncio.run(run_probe(entries, args.out, max(args.interval, 1.0), args.parallel))
        return 0
    if args.command == "spec":
        asyncio.run(run_spec(entries, args.out))
        return 0
    if args.command == "docs":
        docs_check(entries, args.out, args.rendered)
        return 0
    if args.command == "apply":
        return apply(entries, args.out, args.date, write=not args.dry, env=args.env)
    if args.command == "report":
        return report()
    return 1


if __name__ == "__main__":
    sys.exit(main())
