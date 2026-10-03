"""HTTP transport for adapters: one httpx client per server, a token bucket from the catalog's
rate limit, 429 handling with Retry-After, and secret scrubbing on every error message."""

import asyncio
import base64
import time

import httpx

from . import netguard
from .credentials import register_secret, scrub
from .errors import AuthError, InvalidInput, PlatformError, RateLimited, classify, message_for



def _cookies_in_header_order(resp) -> list[tuple[str, str]]:
    """The response's cookies in Set-Cookie order (the jar's own order differs between Python versions; the
    TypeScript runtime replays them in header order too)."""
    jar = dict(resp.cookies.items())
    names: list[str] = []
    for line in resp.headers.get_list("set-cookie"):
        name = line.split("=", 1)[0].strip()
        if name in jar and name not in names:
            names.append(name)
    return [(n, jar[n]) for n in names] + [(k, v) for k, v in jar.items() if k not in names]

class TokenBucket:
    def __init__(self, per_second: float, burst: int | None = None):
        self.rate = max(per_second, 0.01)
        self.capacity = burst or max(int(self.rate), 1)
        self.tokens = float(self.capacity)
        self.updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def take(self) -> None:
        async with self._lock:
            now = time.monotonic()
            self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
            self.updated = now
            if self.tokens < 1:
                await asyncio.sleep((1 - self.tokens) / self.rate)
                self.tokens = 0
                self.updated = time.monotonic()  # the token earned while sleeping was just spent: refill from now
            else:
                self.tokens -= 1


def auth_headers(auth: dict, creds: dict[str, str]) -> dict[str, str]:
    kind = auth.get("type", "none")
    extra = {h: creds[f] for h, f in (auth.get("extra_headers") or {}).items() if creds.get(f)}
    if kind in ("path", "session", "oauth2_client_credentials", "oauth2_refresh_token"):
        return extra  # substituted into the URL, or a token the transport obtains and attaches itself
    if kind in ("none", "query"):
        return extra
    if kind == "bearer":
        return {**extra, "Authorization": f"Bearer {creds[auth.get('field', 'token')]}"}
        return {"Authorization": f"Bearer {creds[auth.get('field', 'token')]}"}
    if kind == "header":
        if auth.get("headers"):  # several credential-carrying headers: header name -> credential field
            return {**extra, **{h: creds[f] for h, f in auth["headers"].items() if creds.get(f)}}
        return {**extra, auth["header"]: auth.get("prefix", "") + creds[auth.get("field", "api_key")]}
    if kind == "basic":
        user = creds.get(auth.get("username_field", "username"), "") if auth.get("username_field") else creds[auth.get("field", "api_key")]
        pwd = creds.get(auth.get("password_field", "password"), "") if auth.get("password_field") else auth.get("password", "")
        token = base64.b64encode(f"{user}:{pwd}".encode()).decode()
        register_secret(token)  # an error body that echoes the Authorization header is redacted too
        return {**extra, "Authorization": "Basic " + token}
    raise InvalidInput(f"unsupported auth type {kind!r} in catalog")


def auth_params(auth: dict, creds: dict[str, str]) -> dict[str, str]:
    """Credential-carrying query parameters: ``type: query`` with one ``param``/``field`` pair, and/or a
    ``params`` map (query parameter name -> credential field) usable with any auth type. Optional
    credentials that were not supplied are simply left out."""
    out: dict[str, str] = {}
    if auth.get("type") == "query" and auth.get("param"):
        value = creds.get(auth.get("field", "api_key"))
        if value:
            out[auth["param"]] = value
    for param, field in (auth.get("params") or {}).items():
        value = creds.get(field)
        if value:
            out[param] = value
    return out


def _local(tag: str) -> str:
    return tag.split("}", 1)[1] if tag.startswith("{") else tag.split(":", 1)[-1]


def _el_to_obj(el):
    attrs = {f"@{_local(k)}": v for k, v in el.attrib.items()}
    kids = list(el)
    text = (el.text or "").strip()
    if not kids and not attrs:
        return text
    out: dict = dict(attrs)
    for kid in kids:
        name, val = _local(kid.tag), _el_to_obj(kid)
        if name in out:
            out[name] = out[name] if isinstance(out[name], list) else [out[name]]
            out[name].append(val)
        else:
            out[name] = val
    if text:
        out["#text"] = text
    return out


def xml_to_obj(text: str) -> dict:
    """XML → {root: …}: elements become keys, repeated elements lists, attributes `@name`,
    mixed text `#text`, leaf values strings; namespace prefixes dropped."""
    import re
    import xml.etree.ElementTree as ET
    if isinstance(text, str):
        # the text is already decoded: drop the declaration's encoding (windows-1251 ...) before handing UTF-8 bytes over
        text = re.sub(r"^(\s*<\?xml[^>]*?)\s+encoding\s*=\s*[\"'][^\"']*[\"']", r"\1", text, count=1).encode("utf-8")
    root = ET.fromstring(text)
    return {_local(root.tag): _el_to_obj(root)}


def obj_to_xml(root: str, obj) -> str:
    """The inverse for request bodies: dict keys → elements, lists → repeated elements, `@x` → attributes."""
    from xml.sax.saxutils import escape, quoteattr

    def node(name, val):
        if isinstance(val, list):
            return "".join(node(name, v) for v in val)
        if isinstance(val, dict):
            attrs = "".join(f" {k[1:]}={quoteattr(str(v))}" for k, v in val.items() if k.startswith("@"))
            inner = "".join(node(k, v) for k, v in val.items() if not k.startswith("@") and k != "#text")
            inner += escape(str(val["#text"])) if "#text" in val else ""
            return f"<{name}{attrs}>{inner}</{name}>"
        if isinstance(val, bool):
            val = "true" if val else "false"
        return f"<{name}>{escape('' if val is None else str(val))}</{name}>"
    return '<?xml version="1.0" encoding="UTF-8"?>' + node(root, obj)


def _set_nested(root: dict, key: str, value) -> None:
    parts = key.split(".")
    for part in parts[:-1]:
        root = root.setdefault(part, {})
    root[parts[-1]] = value


def _form_pairs(body: dict) -> dict:
    """application/x-www-form-urlencoded: scalars as-is, lists as repeated keys, booleans lower-case."""
    out: dict = {}
    for k, v in body.items():
        if isinstance(v, bool):
            out[k] = "true" if v else "false"
        elif isinstance(v, list):
            out[k] = [("true" if x else "false") if isinstance(x, bool) else x for x in v]
        elif isinstance(v, dict):
            import json as _json
            out[k] = _json.dumps(v)
        else:
            out[k] = v
    return out


def body_text(content: bytes, ctype: str) -> str:
    """The body as text, decoded the same way in both runtimes: the Content-Type charset, else the encoding an XML
    declaration names (the Bank of Russia serves windows-1251 XML), else UTF-8; undecodable bytes become U+FFFD."""
    import codecs
    import re
    m = re.search(r"charset\s*=\s*[\"']?([A-Za-z0-9_.:-]+)", ctype or "", re.I)
    enc = m.group(1) if m else None
    if not enc:
        head = content[:300].decode("latin-1").lstrip("\ufeff")
        d = re.match(r"\s*<\?xml[^>]*?encoding\s*=\s*[\"']([A-Za-z0-9_.:-]+)[\"']", head)
        enc = d.group(1) if d else "utf-8"
    try:
        codecs.lookup(enc)
    except LookupError:
        enc = "utf-8"  # an unknown label (BCB declares encoding="pt-br")
    text = content.decode(enc, errors="replace")
    return text[1:] if text.startswith("\ufeff") and enc.lower().replace("-", "") in ("utf8",) else text


def _dig_found(data, path: str) -> tuple[bool, object]:
    """(present, value) for a dotted path (`*` and array indexes as in adapter._dig): an absent key is not a null."""
    cur = data
    for part in path.split("."):
        if part == "*" and isinstance(cur, dict) and cur:
            cur = next(iter(cur.values()))
        elif part == "*" and isinstance(cur, list) and cur:
            cur = cur[0]
        elif isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return False, None
    return True, cur


def _same_json(a, b) -> bool:
    """JSON equality as JavaScript's === sees scalars: a boolean never equals a number (Python's 0 == False)."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    return a == b


def _json_text(v) -> str:
    """A message from any JSON value, identical in both runtimes (strings as-is, the rest as compact JSON)."""
    import json as _json
    return v if isinstance(v, str) else _json.dumps(v, ensure_ascii=False, separators=(",", ":"))


class UnparsedText(dict):
    """A body that is not JSON, XML or CSV ({"text": ...}): a tool that maps records from it fails with the platform's
    content type instead of answering an empty success (an HTML challenge page, a moved-permanently notice)."""

    def __init__(self, text: str, ctype: str = ""):
        super().__init__(text=text)
        self.ctype = ctype


class ResponseCache:
    """A short-lived, bounded cache of successful response bodies (the text, not the parsed tree, so
    memory is bounded by the bytes actually held). LRU by insertion/use; an entry expires after its TTL;
    the total is capped at PLATFORM_MCP_CACHE_MAX_MB (default 64) and PLATFORM_MCP_CACHE_MAX_ENTRIES
    (default 16); a body larger than the cap is never stored. PLATFORM_MCP_CACHE_MAX_MB=0 disables it."""

    def __init__(self, max_bytes: int | None = None, max_entries: int | None = None):
        import os
        from collections import OrderedDict
        def num(name, default):
            try:
                return float(os.environ.get(name, default))
            except ValueError:
                return float(default)
        self.max_bytes = int(max_bytes if max_bytes is not None else num("PLATFORM_MCP_CACHE_MAX_MB", 64) * 1_000_000)
        self.max_entries = int(max_entries if max_entries is not None else num("PLATFORM_MCP_CACHE_MAX_ENTRIES", 16))
        self.enabled = self.max_bytes > 0 and self.max_entries > 0
        self.entries: "OrderedDict[str, tuple[float, int, str, str]]" = OrderedDict()
        self.bytes = 0
        self.hits = self.misses = 0

    def get(self, key: str):
        item = self.entries.get(key)
        if item is None or item[0] < time.monotonic():
            if item is not None:
                self._drop(key)
            self.misses += 1
            return None
        self.entries.move_to_end(key)
        self.hits += 1
        return item[2], item[3], (item[4] if len(item) > 4 else {})

    def put(self, key: str, text: str, ctype: str, ttl: float, headers: dict | None = None) -> None:
        size = len(text.encode("utf-8"))
        if not self.enabled or ttl <= 0 or size > self.max_bytes:
            return
        if key in self.entries:
            self._drop(key)
        while self.entries and (self.bytes + size > self.max_bytes or len(self.entries) >= self.max_entries):
            self._drop(next(iter(self.entries)))
        self.entries[key] = (time.monotonic() + ttl, size, text, ctype, dict(headers or {}))
        self.bytes += size

    def _drop(self, key: str) -> None:
        item = self.entries.pop(key, None)
        if item:
            self.bytes -= item[1]


class Transport:
    def __init__(self, base_url: str, auth: dict, creds: dict[str, str], rate_per_second: float, user_agent: str, timeout: float = 30.0, envelope: dict | None = None):
        self.base_url = base_url.rstrip("/")
        self.auth = auth
        self.creds = creds
        for f in auth.get("fields") or []:  # secret fields: redact their values in every message
            register_secret(creds.get(f["name"] if isinstance(f, dict) else str(f)))
        self._load_rotated_refresh_token()
        self.envelope = envelope or {}
        self.bucket = TokenBucket(rate_per_second)
        self.cache = ResponseCache()
        self.client = httpx.AsyncClient(timeout=timeout, headers={"User-Agent": user_agent, "Accept": "application/json"})
        self.resolve_host = netguard.default_resolver  # tests inject a resolver; see netguard.py

    def _fill_path(self, url: str) -> str:
        """`{token}`-style credential or config placeholders in the base URL or path (Telegram's
        /bot{token}/, a per-install `{instance}` host). Tool arguments are filled by the adapter."""
        for name, value in self.creds.items():
            if value is not None and "{" + name + "}" in url:
                url = url.replace("{" + name + "}", str(value))
        if "{access_token}" in url and self._token:
            url = url.replace("{access_token}", str(self._token))  # the minted session token in the URL path
        return url

    _token: str | None = None
    _token_expires: float = 0.0

    async def _acquire_token(self) -> str:
        """Session logins (Bluesky's createSession) and OAuth2 client-credentials (Reddit) hand
        out short-lived bearer tokens; obtained lazily, cached, refreshed on expiry or 401."""
        kind = self.auth.get("type")
        now_ctx = {"timestamp": str(int(time.time() * 1000)), "timestamp_s": str(int(time.time()))}
        tj = self.auth.get("token_jwt")
        if tj:
            # a JWT built for the token request (client_assertion / private_key_jwt, or a login body field)
            import jwt as _jwt
            jc = {**now_ctx, "nonce": __import__("uuid").uuid4().hex}
            claims = {}
            for k, v in (tj.get("claims") or {}).items():
                if isinstance(v, str) and v.startswith("+") and v[1:].isdigit():
                    claims[k] = int(jc["timestamp_s"]) + int(v[1:])
                else:
                    r = self._render(str(v), jc)
                    claims[k] = int(r) if r.isdigit() and str(v) in ("{timestamp}", "{timestamp_s}") else r
            alg = {"jwt_hs256": "HS256", "jwt_rs256": "RS256", "jwt_ps256": "PS256"}[tj.get("mode", "jwt_rs256")]
            key = self._key_bytes(tj) if alg == "HS256" and tj.get("key_encoding") else self.creds.get(tj.get("key_field", "private_key"), "").replace("\\n", "\n")
            hdr = {k: self._render(str(v), jc) for k, v in (tj.get("jwt_header") or {}).items()} or None
            now_ctx["client_assertion"] = _jwt.encode(claims, key, algorithm=alg, headers=hdr)
        if kind == "session":
            login = self.auth["login"]
            url = self._fill_path(login["path"] if login["path"].startswith("http") else self.base_url + login["path"])
            body = {}
            for k, v in login.get("body", {}).items():
                v = self.creds.get(v[1:]) if isinstance(v, str) and v.startswith("@") and "{" not in v else v
                _set_nested(body, k, self._render(v, now_ctx) if isinstance(v, str) and "{" in v else v)  # nested login bodies: auth.username
            lh = {h: self._render(str(t), now_ctx) for h, t in (login.get("headers") or {}).items()}  # e.g. an API key beside the login
            if login.get("method", "POST").upper() == "GET":
                resp = await self.client.get(url, params=body, headers=lh)  # gettoken?corpid=…&corpsecret=… (WeCom)
            elif login.get("body_format") == "form":
                resp = await self.client.post(url, data=body, headers=lh)
            else:
                resp = await self.client.request(login.get("method", "POST"), url, json=body, headers=lh)
        elif kind in ("oauth2_client_credentials", "oauth2_refresh_token"):
            cid = self.creds[self.auth.get("client_id_field", "client_id")]
            secret = self.creds.get(self.auth.get("client_secret_field", "client_secret"), "")
            if kind == "oauth2_refresh_token":
                # the user obtained a refresh token once (the platform's consent flow); we mint access tokens from it
                data = {"grant_type": "refresh_token", "refresh_token": self.creds[self.auth.get("refresh_token_field", "refresh_token")]}
            else:
                data = {"grant_type": self.auth.get("grant", "client_credentials")}
            if self.auth.get("scope"):
                data["scope"] = self.auth["scope"]
            for k, v in (self.auth.get("token_params") or {}).items():
                data[k] = self._render(v, now_ctx) if isinstance(v, str) and "{" in v else v
            token_url = self._fill_path(self.auth["token_url"])  # per-install hosts / instances in the token URL
            th = {h: self._render(str(t), now_ctx) for h, t in (self.auth.get("token_headers") or {}).items()}
            basic = None
            if self.auth.get("client_auth", "basic") == "body":
                data["client_id"] = cid
                if secret:
                    data["client_secret"] = secret
            else:
                basic = (cid, secret)
                register_secret(base64.b64encode(f"{cid}:{secret}".encode()).decode())  # the token request's Basic header, if echoed
            renames = self.auth.get("token_fields") or {}
            if renames:
                # platforms that name the grant fields differently (app_id/secret, client_key): {standard: theirs|null}
                data = {renames.get(k, k): v for k, v in data.items() if renames.get(k, k) is not None}
            if self.auth.get("token_sign") or self.auth.get("token_query") or self.auth.get("token_body_extra"):
                # signed token requests (Shopee: sign = HMAC(partner_key, partner_id + path + timestamp))
                from urllib.parse import urlparse
                tctx = dict(now_ctx, path=urlparse(token_url).path, access_token=str(self._token or ""))
                ts = self.auth.get("token_sign")
                if ts:
                    tctx["signature"] = self._encode(self._digest(ts, self._render(ts["payload"], tctx), self._key_bytes(ts)), ts.get("encoding"), ts.get("case"))
                for k, v in (self.auth.get("token_body_extra") or {}).items():
                    as_int = isinstance(v, str) and v.startswith("int:")  # "int:{@partner_id}" → JSON integer
                    r = self._render(str(v)[4:] if as_int else str(v), tctx)
                    data[k] = int(r) if as_int and r.lstrip("-").isdigit() else r
                if self.auth.get("token_query"):
                    from urllib.parse import quote
                    q = "&".join(f"{k}={quote(self._render(str(v), tctx), safe='')}" for k, v in self.auth["token_query"].items())
                    token_url = token_url + ("&" if "?" in token_url else "?") + q
            if self.auth.get("token_method", "POST").upper() == "GET":
                resp = await self.client.get(token_url, params=data, headers=th, auth=basic)
            elif self.auth.get("token_body") == "json":
                resp = await self.client.post(token_url, json=data, headers=th, auth=basic)
            else:
                resp = await self.client.post(token_url, data=data, headers=th, auth=basic)
        else:
            raise InvalidInput(f"no token flow for auth type {kind!r}")
        if resp.status_code in (400, 401, 403):
            raise AuthError(scrub(f"token request refused ({resp.status_code}): {resp.text[:200]}"), status=resp.status_code)
        if resp.status_code >= 400:
            raise PlatformError(scrub(f"token request failed ({resp.status_code})"), status=resp.status_code)
        if self.auth.get("token_from_cookie") == "*":
            payload, token = {}, "; ".join(f"{k}={v}" for k, v in _cookies_in_header_order(resp)) or None  # replay every login cookie
        elif self.auth.get("token_from_cookie"):
            payload, token = {}, resp.cookies.get(self.auth["token_from_cookie"])  # sessions handed back as Set-Cookie
        elif self.auth.get("token_from_header"):
            # tokens handed back in a response header (e.g. X-Auth-Token) rather than the body
            payload, token = {}, resp.headers.get(self.auth["token_from_header"])
        else:
            payload = resp.json() if resp.text.strip()[:1] in "{[" else (xml_to_obj(resp.text) if resp.text.strip()[:1] == "<" else {})
            token = payload
            for part in self.auth.get("token_path", "access_token").split("."):
                token = token.get(part) if isinstance(token, dict) else None
        if not isinstance(token, str) or not token:
            raise AuthError("token response carried no token")
        ttl = payload
        for part in self.auth.get("expires_path", "expires_in").split("."):  # nested expiry: data.expires_in
            ttl = ttl.get(part) if isinstance(ttl, dict) else None
        register_secret(token)
        rotated = payload
        for part in self.auth.get("refresh_token_path", "refresh_token").split("."):
            rotated = rotated.get(part) if isinstance(rotated, dict) else None
        if kind == "oauth2_refresh_token" and isinstance(rotated, str) and rotated:
            self._store_rotated_refresh_token(rotated)  # single-use refresh tokens (Allegro, Mercado Libre; nested: data.refresh_token)
        self._token = token
        self._token_expires = time.monotonic() + (float(ttl) - 30 if isinstance(ttl, (int, float)) and ttl > 60 else float(self.auth.get("token_ttl_seconds", 1800)))
        return token

    def _state_file(self):
        """Opt-in persistence of rotated refresh tokens: PLATFORM_MCP_STATE_DIR/<platform>.json (0600)."""
        import os
        from pathlib import Path
        root, key = os.environ.get("PLATFORM_MCP_STATE_DIR"), self.auth.get("state_key")
        return Path(root) / f"{key}.json" if root and key else None

    def _load_rotated_refresh_token(self) -> None:
        if self.auth.get("type") != "oauth2_refresh_token":
            return
        path = self._state_file()
        if path and path.exists():
            import json as _json
            try:
                saved = _json.loads(path.read_text(encoding="utf-8")).get("refresh_token")
            except (OSError, ValueError):
                saved = None
            if isinstance(saved, str) and saved:
                self.creds[self.auth.get("refresh_token_field", "refresh_token")] = saved
                register_secret(saved)

    def _store_rotated_refresh_token(self, value: str) -> None:
        field = self.auth.get("refresh_token_field", "refresh_token")
        if self.creds.get(field) == value:
            return
        register_secret(value)
        self.creds[field] = value  # the next refresh in this process uses the new one
        path = self._state_file()
        if path:
            import json as _json
            import os
            import tempfile
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            # a fresh, exclusively created temp file (0600, never a planted symlink), then an atomic rename
            fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    fh.write(_json.dumps({"refresh_token": value}))
                os.chmod(tmp, 0o600)
                os.replace(tmp, path)
            except BaseException:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise

    def _render(self, template: str, ctx: dict) -> str:
        import re as _re
        return _re.sub(r"\{(@?[A-Za-z_][A-Za-z0-9_]*)\}", lambda m: str(self.creds.get(m.group(1)[1:], "") if m.group(1).startswith("@") else ctx.get(m.group(1), m.group(0))), template)

    @staticmethod
    def _encode(digest: bytes, encoding: str | None, case: str | None) -> str:
        if encoding == "base64":
            out = base64.b64encode(digest).decode()
        elif encoding == "base64url":
            out = base64.urlsafe_b64encode(digest).decode().rstrip("=")
        elif encoding == "base64_hex":  # Base64 of the hex digest text (SHEIN)
            out = base64.b64encode(digest.hex().encode()).decode()
        else:
            out = digest.hex()
        return out.upper() if case == "upper" else out

    def _key_bytes(self, spec: dict, field: str | None = None) -> bytes:
        raw = self.creds.get(field or spec.get("key_field", "api_secret"), "") or ""
        enc = spec.get("key_encoding")
        if enc in ("base64", "base64url"):
            pad = "=" * (-len(raw) % 4)
            return base64.urlsafe_b64decode(raw + pad) if enc == "base64url" else base64.b64decode(raw + pad)
        if enc == "hex":
            return bytes.fromhex(raw)
        return raw.encode()

    def _digest(self, spec: dict, payload: str, secret: bytes) -> bytes:
        import hashlib
        import hmac
        algo = getattr(hashlib, spec.get("algorithm", "sha256"))
        mode = spec.get("mode", "hmac")
        return algo(payload.encode()).digest() if mode == "hash" else hmac.new(secret, payload.encode(), algo).digest()

    def _sign(self, method: str, base: str, pairs: list[str], body_str: str, body_obj=None, form_kv: list | None = None) -> tuple[list[str], dict[str, str], str | None]:
        """auth.sign: request signing. Payload/header/param templates may use {timestamp} (ms), {timestamp_s},
        {timestamp_iso}, {timestamp_fmt} (timestamp_format in timestamp_offset), {method}, {path} (minus
        path_strip), {query}, {query_q}, {body}, {sorted_params}, {sorted_query}, {sorted_values}, {sorted_kv},
        {sorted_body}, {nonce}, {access_token}, pre-computed digests (`pre`) and {@credential}. Modes: hmac, hash,
        rsa_sha256, jwt_hs256, jwt_rs256, aws_sigv4, oauth1. Returns (pairs, headers, body_signature)."""
        spec = self.auth.get("sign")
        if not spec:
            return pairs, {}, None
        from datetime import datetime, timedelta, timezone
        from urllib.parse import quote, unquote, urlparse
        now = time.time()
        utc = datetime.fromtimestamp(now, timezone.utc)
        ctx = {"timestamp": str(int(now * 1000)), "timestamp_s": str(int(now)),
               "timestamp_iso": utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{int(now * 1000) % 1000:03d}Z",
               "datetime_compact": utc.strftime("%y%m%dT%H%M%SZ"), "amz_date": utc.strftime("%Y%m%dT%H%M%SZ"), "date": utc.strftime("%Y%m%d"),
               "nonce": __import__("uuid").uuid4().hex, "access_token": str(self._token or "")}
        if spec.get("timestamp_format"):
            off = spec.get("timestamp_offset", "+00:00")
            sign_, hh, mm = (1 if off[0] != "-" else -1), int(off[1:3]), int(off[4:6])
            local = utc + timedelta(hours=sign_ * hh, minutes=sign_ * mm)
            from .adapter import _fmt_when
            ctx["timestamp_fmt"] = _fmt_when(spec["timestamp_format"], local)
        pairs = list(pairs)
        if spec.get("timestamp_param"):
            pairs.append(f"{spec['timestamp_param']}={quote(ctx[spec.get('timestamp_value', 'timestamp')], safe='')}")
        for k, v in (spec.get("params") or {}).items():
            pairs.append(f"{k}={quote(self._render(str(v), ctx), safe='')}")
        query = "&".join(pairs)
        kv = sorted((unquote(p.split("=", 1)[0]), unquote(p.split("=", 1)[1]) if "=" in p else "") for p in pairs if p)
        kv = [(k, v) for k, v in kv if k not in set(spec.get("exclude") or [])]  # params the platform leaves out of the signature
        path = urlparse(base).path
        if spec.get("path_strip") and path.startswith(spec["path_strip"]):
            path = path[len(spec["path_strip"]):] or "/"
        body_kv = []
        if isinstance(body_obj, dict):
            import json as _json
            body_kv = sorted((k, v if isinstance(v, str) else _json.dumps(v, separators=(",", ":"), ensure_ascii=False)) for k, v in body_obj.items() if v is not None)
        ctx.update(method=method.upper(), path=path, query=query, query_q=("?" + query if query else ""), body=body_str or "",
                   sorted_params="".join(k + v for k, v in kv), sorted_query="&".join(f"{k}={v}" for k, v in kv),
                   sorted_values="".join(v for _, v in kv), sorted_kv="".join(f"{k}={v}" for k, v in kv),
                   sorted_body="".join(k + v for k, v in body_kv))
        for step in spec.get("pre") or []:  # nested digests: md5(key + md5(timestamp))
            ctx[step["name"]] = self._encode(self._digest(step, self._render(step["payload"], ctx), self._key_bytes(step)), step.get("encoding"), step.get("case"))
        mode = spec.get("mode", "hmac")
        extra_headers: dict[str, str] = {}
        if mode in ("jwt_hs256", "jwt_rs256"):
            import jwt as _jwt
            claims = {}
            for k, v in (spec.get("claims") or {}).items():
                if isinstance(v, str) and v.startswith("+") and v[1:].isdigit():
                    claims[k] = int(ctx["timestamp_s"]) + int(v[1:])  # "+300" → expiry 5 minutes from now
                else:
                    r = self._render(str(v), ctx)
                    claims[k] = int(r) if r.isdigit() and str(v).strip("{}") in ("timestamp", "timestamp_s") else r
            key = self._key_bytes(spec) if mode == "jwt_hs256" and spec.get("key_encoding") else self.creds.get(spec.get("key_field", "api_secret"), "").replace("\\n", "\n")
            header = {k: self._render(str(v), ctx) for k, v in (spec.get("jwt_header") or {}).items()} or None
            signature = _jwt.encode(claims, key, algorithm="HS256" if mode == "jwt_hs256" else "RS256", headers=header)
        elif mode == "rsa_sha256":
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
            pem = self.creds.get(spec.get("key_field", "private_key"), "").replace("\\n", "\n").encode()
            key = serialization.load_pem_private_key(pem, password=None)
            raw = key.sign(self._render(spec["payload"], ctx).encode(), padding.PKCS1v15(), hashes.SHA256())
            signature = self._encode(raw, spec.get("encoding", "base64"), spec.get("case"))
        elif mode == "aws_sigv4":
            import hashlib
            import hmac as _hmac
            region, service = self._render(spec.get("region", "{@region}"), ctx), spec["service"]
            host = urlparse(base).netloc
            canon_q = "&".join(f"{quote(k, safe='-_.~')}={quote(v, safe='-_.~')}" for k, v in kv)
            payload_hash = hashlib.sha256((body_str or "").encode()).hexdigest()
            signed = {"host": host, "x-amz-date": ctx["amz_date"]}
            tok = self.creds.get(spec.get("session_token_field", "session_token"))
            if tok:
                signed["x-amz-security-token"] = tok
            names = sorted(signed)
            canonical = "\n".join([method.upper(), quote(urlparse(base).path or "/", safe="/-_.~"), canon_q,
                                   "".join(f"{n}:{signed[n]}\n" for n in names), ";".join(names), payload_hash])
            scope = f"{ctx['date']}/{region}/{service}/aws4_request"
            to_sign = "\n".join(["AWS4-HMAC-SHA256", ctx["amz_date"], scope, hashlib.sha256(canonical.encode()).hexdigest()])
            k = ("AWS4" + self.creds.get(spec.get("secret_key_field", "secret_access_key"), "")).encode()
            for part in (ctx["date"], region, service, "aws4_request"):
                k = _hmac.new(k, part.encode(), hashlib.sha256).digest()
            signature = _hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()
            extra_headers = {"X-Amz-Date": ctx["amz_date"],
                             "Authorization": f"AWS4-HMAC-SHA256 Credential={self.creds.get(spec.get('access_key_field', 'access_key_id'), '')}/{scope}, SignedHeaders={';'.join(names)}, Signature={signature}"}
            if tok:
                extra_headers["X-Amz-Security-Token"] = tok
        elif mode == "oauth1":
            import hashlib
            import hmac as _hmac
            enc = lambda x: quote(str(x), safe="-._~")  # noqa: E731 - RFC 5849 percent-encoding
            oauth = {"oauth_consumer_key": self.creds.get(spec.get("consumer_key_field", "consumer_key"), ""),
                     "oauth_nonce": ctx["nonce"], "oauth_signature_method": "HMAC-SHA1", "oauth_timestamp": ctx["timestamp_s"], "oauth_version": "1.0"}
            if self.creds.get(spec.get("token_field", "access_token")):
                oauth["oauth_token"] = self.creds[spec.get("token_field", "access_token")]
            # RFC 5849 3.4.1.3.1: form-encoded body parameters are signed with the query and oauth_* parameters
            allp = sorted([(enc(k), enc(v)) for k, v in kv] + [(enc(k), enc(v)) for k, v in (form_kv or [])] + [(enc(k), enc(v)) for k, v in oauth.items()])
            base_str = "&".join([method.upper(), enc(base.split("?")[0]), enc("&".join(f"{k}={v}" for k, v in allp))])
            key = f"{enc(self.creds.get(spec.get('consumer_secret_field', 'consumer_secret'), ''))}&{enc(self.creds.get(spec.get('token_secret_field', 'access_token_secret'), ''))}"
            signature = base64.b64encode(_hmac.new(key.encode(), base_str.encode(), hashlib.sha1).digest()).decode()
            oauth["oauth_signature"] = signature
            extra_headers = {"Authorization": "OAuth " + ", ".join(f'{enc(k)}="{enc(v)}"' for k, v in sorted(oauth.items()))}
        else:
            signature = self._encode(self._digest(spec, self._render(spec["payload"], ctx), self._key_bytes(spec)), spec.get("encoding"), spec.get("case"))
        ctx["signature"] = signature
        if spec.get("body_field"):
            return pairs, {**extra_headers, **{h: self._render(str(t), ctx) for h, t in (spec.get("headers") or {}).items()}}, signature
        if spec.get("signature_param"):
            pairs.append(f"{spec['signature_param']}={quote(signature, safe='')}")
        return pairs, {**extra_headers, **{h: self._render(str(t), ctx) for h, t in (spec.get("headers") or {}).items()}}, None

    async def _dynamic_headers(self, force: bool = False) -> dict[str, str]:
        if self.auth.get("type") not in ("session", "oauth2_client_credentials", "oauth2_refresh_token"):
            return {}
        if force or not self._token or time.monotonic() >= self._token_expires:
            await self._acquire_token()
        if self.auth.get("token_param") or self.auth.get("header") == "":
            return {}  # sent as a query parameter or only via cookies instead
        return {self.auth.get("header", "Authorization"): self.auth.get("prefix", "Bearer ") + str(self._token)}

    def _cookie_header(self) -> dict[str, str]:
        """auth.cookies {name: template}: cookie-borne sessions (token, timestamp, unique id per request)."""
        tpl = self.auth.get("cookies")
        if not tpl:
            return {"Cookie": str(self._token)} if self.auth.get("token_from_cookie") == "*" and self._token else {}
        ctx = {"access_token": str(self._token or ""), "timestamp": str(int(time.time() * 1000)), "timestamp_s": str(int(time.time())),
               "nonce": __import__("uuid").uuid4().hex}
        return {"Cookie": "; ".join(f"{k}={self._render(str(v), ctx)}" for k, v in tpl.items())}

    async def _download(self, url: str, field: str) -> tuple[bytes, str]:
        """A multipart `file:<arg>` part. The URL is a tool argument, so it may come from text the model read:
        every hop (redirects are followed one at a time, at most 5) must resolve to public addresses only
        (netguard), and the body is capped at PLATFORM_MCP_MAX_DOWNLOAD_MB (default 50)."""
        import os
        try:
            cap = int(float(os.environ.get("PLATFORM_MCP_MAX_DOWNLOAD_MB", 50)) * 1_000_000)
        except ValueError:
            cap = 50_000_000
        for _ in range(6):
            vetted = await netguard.check_url(url, self.resolve_host, what=f"the {field} URL")
            target, pin_headers, ext = netguard.pin(url, vetted)  # connect to the vetted address: no second DNS answer
            async with self.client.stream("GET", target, follow_redirects=False, headers={"Accept": "*/*", **pin_headers}, extensions=ext) as got:
                if got.status_code in (301, 302, 303, 307, 308) and got.headers.get("location"):
                    url = str(httpx.URL(url).join(got.headers["location"]))
                    continue
                if got.status_code >= 400:
                    raise InvalidInput(f"could not download {field} from the given URL ({got.status_code})")
                size = got.headers.get("content-length", "")
                if size.isdigit() and int(size) > cap:
                    raise InvalidInput(f"{field}: the file is larger than PLATFORM_MCP_MAX_DOWNLOAD_MB")
                buf = bytearray()
                async for chunk in got.aiter_bytes():
                    buf += chunk
                    if len(buf) > cap:
                        raise InvalidInput(f"{field}: the file is larger than PLATFORM_MCP_MAX_DOWNLOAD_MB")
                return bytes(buf), got.headers.get("content-type", "application/octet-stream")
        raise InvalidInput(f"could not download {field}: too many redirects")

    async def request(self, method: str, path: str, *, params: dict | None = None, json=None, form: bool = False,
                      headers: dict | None = None, query_safe: str = "", sign: bool = True, xml_root: str | None = None,
                      multipart: bool = False, cache_ttl: float | None = None, want_headers: bool = False, csv: dict | None = None,
                      read: bool | None = None) -> object:
        cache_key = None
        if cache_ttl and not multipart and self.cache.enabled:
            # read tools that fetch a whole collection (result.slice / trim / cache_ttl): paging through it
            # reuses one download for cache_ttl seconds instead of fetching everything on every call
            import json as _json
            cache_key = _json.dumps([method.upper(), path, sorted((params or {}).items(), key=lambda kv: kv[0]), json], default=str, sort_keys=True)
            hit = self.cache.get(cache_key)
            if hit is not None:
                data = self._decode(hit[0], hit[1], method, csv)
                return (data, hit[2]) if want_headers else data
        await self.bucket.take()
        downloads: dict = {}  # multipart files are fetched once, even when the request is sent twice
        token_auth = self.auth.get("type") in ("session", "oauth2_client_credentials", "oauth2_refresh_token")
        resp = await self._send(method, path, params, json, form, headers, query_safe, sign, xml_root, multipart, downloads, force=False)
        if resp.status_code == 401 and token_auth:
            # expired token: log in once more and REBUILD the request, because the token may sit in the
            # query (token_param), the path ({access_token}), the body (token_body_path), a cookie or a signature
            resp = await self._send(method, path, params, json, form, headers, query_safe, sign, xml_root, multipart, downloads, force=True)
        text, ctype = body_text(resp.content, resp.headers.get("content-type", "")), resp.headers.get("content-type", "")
        if resp.status_code >= 400:
            # the kind tells the model whom to act on: its arguments (invalid_input, not_found, conflict),
            # the credentials (auth_error), time (rate_limited) or the platform (upstream_error); a read verb is
            # classified as a read whatever its HTTP method (a 404 on a GraphQL/SOAP POST read is not_found)
            kind = classify(resp.status_code, text, method=("GET" if read else method) if read is not None else method, rules=getattr(self, "error_kinds", None))
            retry = resp.headers.get("Retry-After")
            if kind is RateLimited:
                raise RateLimited("rate limited by the platform" + (f" ({resp.status_code}): {scrub(text[:200])}" if resp.status_code != 429 else ""),
                                  retry_after=float(retry) if retry and retry.isdigit() else None, status=resp.status_code)
            raise kind(scrub(message_for(kind, resp.status_code, text)), status=resp.status_code)
        data = self._decode(text, ctype, method, csv)
        resp_headers = {k.lower(): resp.headers.get(k) for k in resp.headers.keys()}
        if cache_key is not None and resp.status_code < 300:
            self.cache.put(cache_key, text, ctype, cache_ttl, resp_headers)  # only successes (envelope failures raised above)
        return (data, resp_headers) if want_headers else data

    async def _send(self, method, path, params, json, form, headers, query_safe, sign, xml_root, multipart, downloads, *, force: bool):
        """Build one request from scratch (token, URL, query, body, signature) and send it."""
        dyn = await self._dynamic_headers(force=force)  # mint first: the token may also go into the path or body
        url = self._fill_path(path if path.startswith("http") else self.base_url + path)
        tool_headers = headers or {}
        headers = dict(getattr(self, "fixed_headers", None) or {})  # adapter.headers: static per-platform headers
        headers.update(tool_headers)  # tool.headers: per-endpoint (vendor media type, X-RestLi-Method)
        headers.update(auth_headers(self.auth, self.creds))
        headers.update(dyn)
        if self.auth.get("token_body_path") and self._token and isinstance(json, dict):
            import copy as _copy
            json = _copy.deepcopy(json)
            _set_nested(json, self.auth["token_body_path"], str(self._token))  # token inside the JSON body (Baidu header.accessToken)
        headers.update(self._cookie_header())
        query = {k: v for k, v in (params or {}).items() if v is not None and v != ""}
        query.update(auth_params(self.auth, self.creds))
        if self.auth.get("token_param") and self._token:
            query[self.auth["token_param"]] = self._token
        # keep a query string written into the path (…?q=search) and encode everything ourselves, so
        # `query_safe` characters (Rest.li's `(),:`) reach the platform literally
        from urllib.parse import quote
        base, _, inline = url.partition("?")
        pairs = [inline] if inline else []
        for k, v in query.items():
            for item in (v if isinstance(v, list) else [v]):
                item = ("true" if item else "false") if isinstance(item, bool) else item
                pairs.append(f"{quote(str(k), safe=query_safe + '[]')}={quote(str(item), safe=query_safe)}")
        if multipart and json is not None:
            # multipart/form-data: text fields as-is, `file:<url>` fields downloaded (guarded) and attached
            files = {}
            for k, v in json.items():
                if isinstance(v, dict) and "_json_part" in v:
                    import json as _json
                    files[k] = (None, _json.dumps(v["_json_part"], ensure_ascii=False), "application/json")
                    continue
                if isinstance(v, dict) and "_file_url" in v:
                    if k not in downloads:
                        downloads[k] = await self._download(v["_file_url"], k)
                    content, ctype = downloads[k]
                    name = v["_file_url"].split("?")[0].rstrip("/").rsplit("/", 1)[-1] or k
                    files[k] = (name, content, ctype)
                else:
                    files[k] = (None, "true" if v is True else "false" if v is False else str(v))
            body, body_str = {"files": files}, ""
        elif xml_root and json is not None:
            body_str = obj_to_xml(xml_root, json)
            body = {"content": body_str.encode("utf-8")}
            if not any(h.lower() == "content-type" for h in headers):
                headers["Content-Type"] = "application/xml"
        elif form and json is not None:
            body = {"data": _form_pairs(json)}
            body_str = "&".join(f"{quote(str(k))}={quote(str(v))}" for k, v in _form_pairs(json).items() if not isinstance(v, list))
        elif json is not None:
            import json as _json
            spec = self.auth.get("sign") or {}
            if sign and spec.get("body_field") and isinstance(json, dict):
                # the signature is computed over the body's own fields and travels inside the body (Temu)
                _p, _h, body_sig = self._sign(method, base, list(pairs), "", body_obj=json)
                json = {**json, spec["body_field"]: body_sig}
            body_str = _json.dumps(json, separators=(",", ":"), ensure_ascii=False)  # the exact bytes that are signed and sent
            body = {"content": body_str.encode("utf-8")}
            if not any(h.lower() == "content-type" for h in headers):
                headers["Content-Type"] = "application/json"
        else:
            body, body_str = {}, ""
        form_kv = [(str(k), ("true" if x else "false") if isinstance(x, bool) else str(x)) for k, v in _form_pairs(json).items() for x in (v if isinstance(v, list) else [v])] if form and isinstance(json, dict) else None
        pairs, sign_headers, _ = self._sign(method, base, pairs, body_str, body_obj=json if isinstance(json, dict) else None, form_kv=form_kv) if sign else (pairs, {}, None)  # tool `sign: false`: public endpoints that reject extra params
        headers.update(sign_headers)
        url = base + ("?" + "&".join(pairs) if pairs else "")
        try:
            return await self._follow(method, url, headers, body)
        except httpx.HTTPError as exc:
            raise PlatformError(scrub(f"network error: {exc.__class__.__name__}"))

    async def _follow(self, method: str, url: str, headers: dict, body: dict):
        """Send one built request and follow its redirects (both runtimes identically) only within the same
        origin (scheme, host, port): a cross-origin Location is refused so no credential header or query parameter is
        replayed to another host. 303 (and 301/302 after a non-GET) continue as a GET without a body. At most 5 hops;
        a 3xx that cannot be followed is an error, never an empty success."""
        from urllib.parse import urljoin, urlsplit
        resp = await self.client.request(method, url, headers=headers, **body)
        hops = 0
        while resp.status_code in (301, 302, 303, 307, 308) and resp.headers.get("location"):
            target = urljoin(url, resp.headers["location"])
            if urlsplit(target)[:2] != urlsplit(url)[:2]:
                raise PlatformError(scrub(f"the platform redirected ({resp.status_code}) to another host, {urlsplit(target).netloc}; not followed so no credential leaves {urlsplit(url).netloc}"), status=resp.status_code)
            hops += 1
            if hops > 5:
                raise PlatformError(f"too many redirects ({resp.status_code})", status=resp.status_code)
            if resp.status_code == 303 or (resp.status_code in (301, 302) and method.upper() not in ("GET", "HEAD")):
                method, body = "GET", {}
                headers = {k: v for k, v in headers.items() if k.lower() != "content-type"}
            url = target
            resp = await self.client.request(method, url, headers=headers, **body)
        if 300 <= resp.status_code < 400:
            raise PlatformError(f"the platform answered {resp.status_code} without a redirect that can be followed", status=resp.status_code)
        return resp

    def _decode(self, text: str, ctype: str, method: str, csv: dict | None = None) -> object:
        """Parse a successful body (JSON, XML, CSV or text) and apply the envelope rules. A tool's `csv`
        ({delimiter, skip_lines}) parses the body as delimited text whatever its content type (CNB serves
        pipe-separated text/plain with a date line first; SNB a semicolon CSV with a preamble)."""
        if not text.strip():
            return {}  # 204 No Content and empty 200 bodies
        if "csv" in ctype or csv is not None:
            import csv as _csv
            import io as _io
            opts = csv or {}
            body = text.lstrip("\ufeff")
            if opts.get("skip_lines"):
                body = "\n".join(body.splitlines()[int(opts["skip_lines"]):])
            rows = list(_csv.DictReader(_io.StringIO(body), delimiter=str(opts.get("delimiter") or ",")))
            return {"rows": [{k: v for k, v in r.items() if k is not None and k != ""} for r in rows if any(v not in (None, "") for v in r.values())]}  # CSV → {"rows": [{header: value}]}
        import re as _re
        if "text/html" in ctype.lower() or _re.match(r"\s*<(?:!doctype\s+html|html[\s>])", text[:200], _re.I):
            return UnparsedText(text, ctype or "text/html")  # an HTML page (a challenge, an error page) is never an API record, even when it parses as XML
        is_xml = "xml" in ctype or text.lstrip()[:1] == "<"
        if is_xml or "json" in ctype or text[:1] in "{[":
            try:
                import json as _json
                data = xml_to_obj(text) if is_xml and text.lstrip()[:1] == "<" else _json.loads(text)
            except Exception:
                return UnparsedText(text, ctype)
            env = self.envelope
            failed = False
            if env and isinstance(data, dict) and env.get("ok_field") in data:
                # ok when the field is truthy, or equals `ok_value` (TikTok/Bybit/OKX answer code 0 on success)
                okv = env.get("ok_value")
                failed = (data[env["ok_field"]] not in (okv if isinstance(okv, list) else [okv])) if "ok_value" in env else not data.get(env["ok_field"])
            msg = None

            def dig(path: str):
                from .adapter import _dig
                return _dig(data, path)
            present = False
            for path in (env or {}).get("fail_if_present") or []:
                # an error list/object that is present and non-empty means failure (Kraken {"error": ["EQuery:…"]},
                # GraphQL {"errors": [{"message": …}]}); the message is error_field, else the value itself
                found = dig(path)
                if found not in (None, "", [], {}):
                    failed = True
                    detail = dig(env["error_field"]) if env.get("error_field") else None
                    if detail in (None, ""):
                        detail = found
                    msg = _json_text(detail)
                    present = True
                    break
            for path, value in ((env or {}).get("fail_when") or {}).items():
                # a notice served as a normal 200 document (a feed whose only item says 'Too Many Requests',
                # a decoder whose record comes back empty: {"Results.0.Make": ""}); `null` matches an explicit
                # null only, never an absent path (a list answer has no data.last), and 0 never equals false
                found, got = _dig_found(data, path)
                if not present and found and _same_json(got, value):
                    failed = True
                    detail = dig(env["error_field"]) if env.get("error_field") else None
                    msg = _json_text(detail) if detail not in (None, "") else (f"{path} is null" if value is None else _json_text(value))
            if failed:
                # platforms that report failures inside a 200 body (Slack, Telegram)
                if msg is None:
                    detail = dig(env.get("error_field", "error")) if isinstance(data, dict) else None
                    msg = _json_text(detail if detail is not None else "request failed")
                kind = classify(200, msg, method=method, rules=getattr(self, "error_kinds", None), envelope=True)
                raise kind(scrub(msg) if kind in (RateLimited, AuthError) else scrub(msg)[:300], status=200)
            return data
        return UnparsedText(text, ctype)

    async def aclose(self) -> None:
        await self.client.aclose()
