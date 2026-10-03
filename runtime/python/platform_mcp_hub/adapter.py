"""Declarative adapter interpreter. The catalog's ``adapter`` block maps each category verb to an
HTTP call and a field mapping; the same block drives the TypeScript runtime. Nothing here knows
any platform by name."""

import re
from typing import Any

from .errors import InvalidInput, NotFound, NotSupported
from .http import Transport

_PATH_VAR = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def _dig(obj: Any, path: str | None) -> Any:
    """Dotted path lookup: ``results`` / ``data.items`` / ``job.title``; ``$`` is the root."""
    if path in (None, "", "$"):
        return obj
    cur = obj
    for part in path.split("."):
        if part == "*":
            # the first value of an object keyed by a name the caller cannot know (Kraken answers
            # {"result": {"XXBTZUSD": {...}}} for pair=XBTUSD), or the first element of an array
            if isinstance(cur, dict):
                cur = next(iter(cur.values()), None)
            elif isinstance(cur, list):
                cur = cur[0] if cur else None
            else:
                return None
        elif isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list) and part.isdigit():
            cur = cur[int(part)] if int(part) < len(cur) else None
        else:
            return None
    return cur


def _to_number(text: str):
    """A decimal string as a JSON number (None when it is not one); integral values become ints so
    both runtimes serialise them identically ("83989.0" -> 83989)."""
    try:
        f = float(text.strip())
    except ValueError:
        return None
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return int(f) if f.is_integer() and abs(f) < 2 ** 53 else f


def _epoch_iso(value: Any) -> Any:
    from datetime import datetime, timezone
    num = value if isinstance(value, (int, float)) and not isinstance(value, bool) else (_to_number(value) if isinstance(value, str) else None)
    if num is None:
        return None if value in (None, "") else value
    secs = num / 1000 if abs(num) >= 1e11 else num
    return datetime.fromtimestamp(int(secs // 1), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_MONTHS = {m: i + 1 for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"))}


def _iso_from_pattern(pattern: str, value: Any) -> Any:
    """Parse `value` with a %d %m %Y %y %H %M %S pattern (same tokens as datefmt:) into ISO-8601; non-matching values pass through."""
    if not isinstance(value, str) or not value.strip():
        return None if value in (None, "") else value
    rx, order = "", []
    i = 0
    while i < len(pattern):
        tok = pattern[i:i + 2]
        if tok in ("%Y", "%y", "%m", "%d", "%H", "%M", "%S", "%b", "%a"):
            # %b an English month name or abbreviation (Sep, September), %a a weekday name (ignored)
            rx += r"(\d{4})" if tok == "%Y" else r"([A-Za-z]{3,9})" if tok in ("%b", "%a") else r"(\d{1,2})"
            order.append(tok)
            i += 2
        else:
            rx += re.escape(pattern[i])
            i += 1
    m = re.fullmatch(rx, value.strip())
    if not m:
        return value
    parts = dict(zip(order, m.groups()))
    if "%b" in parts:
        month = _MONTHS.get(parts.pop("%b")[:3].lower())
        if month is None:
            return value
        parts["%m"] = str(month)
    parts.pop("%a", None)
    year = int(parts["%Y"]) if "%Y" in parts else 2000 + int(parts.get("%y", 0))
    date = f"{year:04d}-{int(parts.get('%m', 1)):02d}-{int(parts.get('%d', 1)):02d}"
    if any(t in parts for t in ("%H", "%M", "%S")):
        return f"{date}T{int(parts.get('%H', 0)):02d}:{int(parts.get('%M', 0)):02d}:{int(parts.get('%S', 0)):02d}Z"
    return date


def _map_fields(record: Any, fields: dict[str, str], args: dict | None = None) -> dict:
    """Map a raw record (object, or a positional array such as Binance klines) to the vocabulary
    fields. A source of ``=literal`` yields that literal; ids are always strings."""
    out = {}
    for key, src in fields.items():
        if isinstance(src, str) and src.startswith("="):
            out[key] = src[1:]
            continue
        if isinstance(src, str) and "{" in src and not src.startswith("fmt:"):
            # a path segment named by an argument: Bank of Canada observations are {"d": ..., "<series>": {"v": ...}}
            # -> "num:{series_id}.v"; an absent argument leaves no path (null)
            src = re.sub(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", lambda m: str((args or {}).get(m.group(1)) if (args or {}).get(m.group(1)) not in (None, "") else "\x00"), src)
        if isinstance(src, str) and src.startswith("arg:"):
            # arg:<name> — the value of a tool argument (a ticker response that does not repeat its symbol)
            value = (args or {}).get(src[4:])
            out[key] = None if value in (None, "") else value
            continue
        if isinstance(src, str) and src.startswith("fmt:"):
            # fmt:https://site/contest/{id} — a string built from record paths; null when any part is missing
            parts, missing = [], False
            for lit, path in re.findall(r"([^{]*)(?:\{([^{}]+)\})?", src[4:]):
                parts.append(lit)
                if path:
                    v = _dig(record, path)
                    if v in (None, "") or isinstance(v, (dict, list)):
                        missing = True
                    else:
                        parts.append(str(int(v)) if isinstance(v, float) and v.is_integer() else str(v).lower() if isinstance(v, bool) else str(v))
            out[key] = None if missing else "".join(parts)
            continue
        if isinstance(src, str) and src.startswith("iso:"):
            # iso:<path> — epoch seconds (or milliseconds, >= 1e11) as ISO-8601 UTC; other values unchanged
            value = None
            for alt in src[4:].split("|"):
                value = _dig(record, alt)
                if value not in (None, ""):
                    break
            out[key] = _epoch_iso(value)
            continue
        if isinstance(src, str) and src.startswith("isodate:"):
            # isodate:<pattern>:<path> — a date written in the platform's format (%d.%m.%Y, %d/%m/%Y, %Y%m%d) as ISO
            # YYYY-MM-DD (or YYYY-MM-DDTHH:MM:SSZ when the pattern has a time); a value that does not match stays as it is
            rest = src[8:]
            cut = rest.find(":", rest.rfind("%") + 2) if "%" in rest else rest.find(":")
            out[key] = _iso_from_pattern(rest[:cut], _dig(record, rest[cut + 1:]))
            continue
        if isinstance(src, str) and src.startswith("num_comma:"):
            # num_comma:<path> — a decimal-comma number ("14,123", "1 234,5", "1.234,5") as a JSON number
            value = _dig(record, src[10:])
            if isinstance(value, str):
                t = value.strip().replace("\u00a0", "").replace(" ", "")
                value = _to_number(t.replace(".", "").replace(",", ".")) if re.fullmatch(r"[+-]?[0-9.]*,?[0-9]+", t) else None
            out[key] = value
            continue
        as_str = isinstance(src, str) and src.startswith("str:")  # str:<path> — a number the vocabulary types as a string
        as_num = isinstance(src, str) and src.startswith("num:")  # num:<path> — a decimal string the vocabulary types as a number
        value = None
        for alt in (src[4:] if as_str or as_num else src).split("|"):  # a|b — the first alternative that is present
            value = _dig(record, alt)
            if value not in (None, ""):
                break
        if as_str and value is not None and not isinstance(value, (dict, list)):
            if isinstance(value, bool):
                value = str(value).lower()
            elif isinstance(value, float) and value.is_integer():
                value = str(int(value))  # 3.0 -> "3", as JavaScript's String(3.0)
            else:
                value = str(value)
        if as_num and isinstance(value, str):
            value = _to_number(value)
        out[key] = value
    out = {k: (str(v) if (k == "id" or k.endswith("_id")) and v is not None else v) for k, v in out.items()}
    out["raw"] = record if isinstance(record, dict) else {"values": record}
    return out



def _parse_when(v: Any):
    """ISO date or datetime (or epoch seconds) → aware UTC datetime."""
    from datetime import datetime, timezone
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(float(v), timezone.utc)
    text = str(v).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
    try:
        d = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise InvalidInput(f"not an ISO date/datetime: {v!r}")
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


_FMT = {"%Y": "%Y", "%y": "%y", "%m": "%m", "%d": "%d", "%H": "%H", "%M": "%M", "%S": "%S"}


def _fmt_when(pattern: str, d) -> str:
    """strftime restricted to %Y %y %m %d %H %M %S so the TypeScript runtime formats identically."""
    out, i = [], 0
    while i < len(pattern):
        tok = pattern[i:i + 2]
        if tok in _FMT:
            out.append(d.strftime(tok)); i += 2
        else:
            out.append(pattern[i]); i += 1
    return "".join(out)


def _split_key(key: str) -> list[str]:
    """Split a dotted body key; a backslash-escaped dot (``m\\.relates_to``) stays inside the segment."""
    import re
    return [seg.replace("\\.", ".") for seg in re.split(r"(?<!\\)\.", key)]


def _set_path(root: Any, parts: list[str], value: Any) -> None:
    cur = root
    for i, part in enumerate(parts[:-1]):
        nxt_is_index = parts[i + 1].isdigit()
        if isinstance(cur, list):
            idx = int(part)
            while len(cur) <= idx:
                cur.append(None)
            if cur[idx] is None:
                cur[idx] = [] if nxt_is_index else {}
            cur = cur[idx]
        else:
            if part not in cur or cur[part] is None:
                cur[part] = [] if nxt_is_index else {}
            cur = cur[part]
    last = parts[-1]
    if isinstance(cur, list):
        idx = int(last)
        while len(cur) <= idx:
            cur.append(None)
        cur[idx] = value
    else:
        cur[last] = value


_PATH_SAFE = "!$&'()*+,;=:@/"  # RFC 3986 pchar and "/": unreserved and these stay literal
_PCT = re.compile(r"(%[0-9A-Fa-f]{2})")


def encode_path_value(value: Any) -> str:
    """A value spliced into a URL path. Tool arguments come from the model, which may have read hostile
    text: they must not add a query or a fragment or climb out of the endpoint with dot segments. Every
    character outside RFC 3986 pchar (and "/", which ids such as `gb/00102498` or `google/gemma-2b` carry)
    is percent-encoded, an existing %XX escape is kept (pre-encoded URNs), and a "." or ".." segment
    (also as %2E, which URL parsers resolve too) is refused. The TypeScript runtime's encodePathValue is
    identical."""
    from urllib.parse import quote, unquote
    text = str(int(value)) if isinstance(value, float) and value.is_integer() else str(value).lower() if isinstance(value, bool) else str(value)
    for seg in text.split("/"):
        if unquote(seg) in (".", ".."):
            raise InvalidInput("a path argument cannot contain '.' or '..' segments")
    return "".join(part if _PCT.fullmatch(part) else quote(part, safe=_PATH_SAFE) for part in _PCT.split(text))


_PAGING = re.compile(r"(?:^|[^A-Za-z0-9_@])(page|page0|offset|cursor)(?:[^A-Za-z0-9_]|$)")


_NUMBERED = re.compile(r"(?:^|[^A-Za-z0-9_@])(page|page0|offset)(?:[^A-Za-z0-9_]|$)")


def paginates(tool: dict, numbered: bool = False) -> bool:
    """True when the tool sends a page, offset or cursor expression anywhere (params, body, path,
    path_params). A tool that sends none returns the same records for every `page`, so it must
    not advertise a next_page (a client would loop over a repeated first page)."""
    exprs: list[str] = []
    for key in ("params", "body", "path_params"):
        for k, v in (tool.get(key) or {}).items():
            if isinstance(v, str):
                exprs.append(v)
            if "{" in k:
                exprs.append(k)
    exprs.extend(_PATH_VAR.findall(tool.get("path", "")))
    # numbered=True: only page/page0/offset count (a cursor-only tool ignores `page`, so it never offers next_page)
    return bool((tool.get("result") or {}).get("slice")) or any((_NUMBERED if numbered else _PAGING).search(e) for e in exprs)


def _columns_to_rows(cols: dict) -> list[dict]:
    """Parallel arrays ({"t": [1, 2], "o": ["5", "6"]}, TradingView/UDF style) -> one record per index."""
    arrays = {k: v for k, v in cols.items() if isinstance(v, list)}
    n = max((len(v) for v in arrays.values()), default=0)
    return [{k: (v[i] if i < len(v) else None) for k, v in arrays.items()} for i in range(n)]


CURSOR_PREFIX = "pmc1."


def encode_cursor(upstream: Any, offset: int) -> str:
    """A window inside a fixed-size upstream page: pmc1.<base64url of [upstream cursor, offset]> (same bytes in both runtimes)."""
    import base64
    import json as _json
    raw = _json.dumps([upstream, offset], separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return CURSOR_PREFIX + base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[Any, int]:
    """(upstream cursor, offset); anything that is not ours is the platform's own cursor at offset 0."""
    import base64
    import json as _json
    if cursor.startswith(CURSOR_PREFIX):
        body = cursor[len(CURSOR_PREFIX):]
        try:
            upstream, offset = _json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)).decode("utf-8"))
            if isinstance(offset, int) and offset >= 0 and (upstream is None or isinstance(upstream, str)):
                return upstream, offset
        except (ValueError, TypeError):
            pass
        raise InvalidInput("cursor is not one this tool returned; pass next_cursor back unchanged")
    return cursor, 0


def effective_limit(tool: dict, args: dict) -> int:
    """The page size a tool really uses: the `limit` argument (or default_limit), capped by max_limit."""
    return min(int(args.get("limit") or tool.get("default_limit", 25)), int(tool.get("max_limit", 100)))


def apply_cap(items: list, result: dict, limit: int) -> list:
    """result.cap: head|tail — the platform ignores the page size (Kraken OHLC answers 720 candles): keep the
    first or the last `limit` rows."""
    cap = result.get("cap")
    if cap == "head":
        return items[:limit]
    if cap == "tail":
        return items[-limit:] if limit > 0 else []
    return items


def parse_link_header(value: str) -> dict:
    """RFC 8288 Link header -> {rel: url} (`<https://...?page=2>; rel="next", <...>; rel="last"`)."""
    out: dict = {}
    for m in re.finditer(r"<([^>]*)>\s*((?:;\s*[^;,]+)*)", value or ""):
        rel = re.search(r";\s*rel\s*=\s*\"?([^\";,]+)\"?", m.group(2), re.I)
        for r in (rel.group(1).split() if rel else []):
            out.setdefault(r.lower(), m.group(1))
    return out


def from_headers(spec: str, headers: dict) -> Any:
    """`header:<Name>` — a response header's value; `link:<param>` — that query parameter of the Link rel="next" URL
    (`link:` alone: the whole URL). None when absent (no next page)."""
    from urllib.parse import parse_qs, urlsplit
    if spec.startswith("header:"):
        v = headers.get(spec[7:].lower())
        return v if v not in (None, "") else None
    nxt = parse_link_header(headers.get("link", "")).get("next")
    if not nxt:
        return None
    if spec == "link:":
        return nxt
    vals = parse_qs(urlsplit(nxt).query, keep_blank_values=True).get(spec[5:])
    return vals[0] if vals and vals[0] != "" else None


DEFAULT_CACHE_TTL = 60.0


def cache_ttl_for(tool: dict) -> float | None:
    """Seconds a successful response of this tool may be reused: `cache_ttl` on the tool (0 = never), else
    PLATFORM_MCP_CACHE_TTL (default 60) for tools that page a whole collection or a fixed page locally."""
    if "cache_ttl" in tool:
        return float(tool["cache_ttl"] or 0) or None
    result = tool.get("result") or {}
    if result.get("slice") or result.get("trim"):
        import os
        try:
            return float(os.environ.get("PLATFORM_MCP_CACHE_TTL", DEFAULT_CACHE_TTL)) or None
        except ValueError:
            return DEFAULT_CACHE_TTL
    return None


def apply_filters(items: list[dict], rules: Any, args: dict, tool: dict) -> list[dict]:
    """result.filter [{arg, fields, match: contains|equals, value?}]: keep rows where any listed (normalised,
    dotted) field matches the argument, case-insensitively; a rule whose argument is absent keeps every row.
    `value` is an expression for the compared value (a map: from the vocabulary's enum to the platform's)."""
    for rule in rules or []:
        want = Adapter._value(rule["value"], args, tool) if rule.get("value") else args.get(rule["arg"])
        if want in (None, ""):
            continue
        wants = [str(w).lower() for w in (want if isinstance(want, list) else [want])]
        mode = rule.get("match") or "contains"

        def ok(text: str, w: str) -> bool:
            if mode == "equals":
                return text == w
            if mode in ("gte", "lte"):
                # ISO dates/datetimes compare as strings ("since" on a feed); a since of 2026-09-30 keeps that whole day
                return text >= w if mode == "gte" else text[:len(w)] <= w
            return w in text

        def hit(item: dict) -> bool:
            for f in rule.get("fields") or [rule["arg"]]:
                v = _dig(item, f)
                if v is None or isinstance(v, (dict, list)):
                    continue
                text = (str(v).lower() if not isinstance(v, bool) else str(v).lower())
                if any(ok(text, w) for w in wants):
                    return True
            return False
        items = [i for i in items if hit(i)]
    return items


class Adapter:
    def __init__(self, spec: dict, transport: Transport):
        self.spec = spec
        self.transport = transport
        self.tools: dict[str, dict] = spec["adapter"]["tools"]

    def supports(self, verb: str) -> bool:
        return verb in self.tools

    async def call(self, verb: str, args: dict) -> dict:
        tool = self.tools.get(verb)
        if not tool:
            raise NotSupported(f"{self.spec['id']} does not offer {verb}")
        if tool.get("kind") == "probe":
            data = await self._request(tool, args)
            return {"ok": True, "account": data if isinstance(data, dict) else {}}
        result = tool.get("result", {})
        read = self._is_read(verb, tool)
        if self.spec.get("category") == "generic":
            # tools defined by the API's own operations: the answer is passed through (generic.py)
            from . import generic
            data = await self._request(tool, args, cache_ttl=cache_ttl_for(tool), read=read)
            return generic.shape(data, tool, args)
        skip, used_cursor = 0, None
        if result.get("trim") and args.get("cursor"):
            # our own cursor (pmc1.<base64url [upstream cursor, offset]>) addresses a window inside a fixed-size upstream page
            used_cursor, skip = decode_cursor(str(args["cursor"]))
            args = {**args, "cursor": used_cursor}
        headers: dict = {}
        if any(isinstance(result.get(k), str) and result[k].startswith(("link:", "header:")) for k in ("next_cursor", "total")):
            # paging carried in response headers: GitLab keyset `Link: <...id_after=42...>; rel="next"`, X-Total
            data, headers = await self._request(tool, args, cache_ttl=cache_ttl_for(tool), want_headers=True, read=read)
        else:
            data = await self._request(tool, args, cache_ttl=cache_ttl_for(tool), read=read)
        from .http import UnparsedText
        if isinstance(data, UnparsedText) and ("items" in result or "fields" in result):
            from .credentials import scrub
            from .errors import KINDS, RATE_WORDS, PlatformError, RateLimited, _rule_matches
            snippet = " ".join(data["text"].split())[:200]
            # the entry's error_kinds (status 200) first (BCB answers an unknown series with a 200 HTML 'Requisição
            # inválida!' page), then a throttle notice is rate_limited; anything else is the platform's
            kind = next((KINDS[r["kind"]] for r in getattr(self.transport, "error_kinds", None) or []
                         if isinstance(r, dict) and r.get("kind") in KINDS and _rule_matches(r, 200, data["text"])), None)
            raise (kind or (RateLimited if RATE_WORDS.search(data["text"][:2000].lower()) else PlatformError))(scrub(f"the platform answered {data.ctype.split(';')[0] or 'a body'} that is not JSON, XML or CSV: {snippet}"))
        def arg_path(path):
            # {arg} in a result path: CTFtime results are keyed by event id -> items "{competition_id}.scores"
            if not isinstance(path, str) or "{" not in path:
                return path
            return re.sub(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", lambda m: str(args.get(m.group(1))) if args.get(m.group(1)) not in (None, "") else "\x00", path)
        if "items" in result:
            rows = _dig(data, arg_path(result["items"])) or []
            if result.get("columnar") and isinstance(rows, dict):
                rows = _columns_to_rows(rows)
            elif isinstance(rows, dict):
                # collections keyed by id ({"123": {...}, "456": {...}}): the values are the records
                rows = [({**v, "_key": k} if isinstance(v, dict) else v) for k, v in rows.items()] if result.get("items_are_values") else [rows]
            # result.scalar_rows: a list of plain values (Gemini /v1/symbols: ["btcusd", ...]) — each value is a
            # record and `$` names it in result.fields; otherwise scalar rows are not records and are dropped
            rows = [r for r in rows if isinstance(r, (dict, list)) or (result.get("scalar_rows") and r is not None and not isinstance(r, bool))]
            page = int(args.get("page") or 1)
            limit = int(args.get("limit") or tool.get("default_limit", 25))
            fields = result.get("fields", {})
            if result.get("slice"):
                # the platform answers the whole collection: apply page/limit here (capped by max_limit)
                limit = min(limit, int(tool.get("max_limit", 100)))
                lo, hi = (page - 1) * limit, page * limit
                if not (result.get("require") or result.get("sort") or result.get("filter")):
                    # nothing depends on the other rows' mapped values: map only this page's rows
                    return {result.get("key", "items"): [_map_fields(r, fields, args) for r in rows[lo:hi]], "total": len(rows),
                            "next_page": page + 1 if hi < len(rows) else None}
                items = [_map_fields(r, fields, args) for r in rows]
                if result.get("require"):
                    items = [i for i in items if all(i.get(k) is not None for k in result["require"])]
                items = apply_filters(items, result.get("filter"), args, tool)
                every = len(items)
                if result.get("sort"):
                    # a collection answered in no stable order: sort on a normalised field so pages do not overlap
                    items.sort(key=lambda i: str(i.get(result["sort"]) if i.get(result["sort"]) is not None else ""))
                return {result.get("key", "items"): items[lo:hi], "total": every, "next_page": page + 1 if hi < every else None}
            items = [_map_fields(r, fields, args) for r in rows]
            if result.get("require"):
                # drop rows that are not records (feed headers, legal notices, separators)
                items = [i for i in items if all(i.get(k) is not None for k in result["require"])]
            # filters on a verb that does not page (get_series over a long-format CSV: SNB rows per date x dimension)
            items = apply_filters(items, result.get("filter"), args, tool)
            limit = effective_limit(tool, args)  # the page size actually requested (capped by max_limit)
            items = apply_cap(items, result, limit)
            out: dict[str, Any] = {result.get("key", "items"): items}
            total = from_headers(result["total"], headers) if str(result.get("total", "")).startswith(("link:", "header:")) else (_dig(data, result["total"]) if result.get("total") else None)
            out["total"] = int(total) if isinstance(total, (int, float)) and not isinstance(total, bool) else (int(total) if isinstance(total, str) and total.strip().isdigit() else None)
            out["next_page"] = page + 1 if paginates(tool, numbered=True) and len(items) >= limit and (out["total"] is None or page * limit < out["total"]) else None
            if result.get("next_cursor"):
                # cursor-paginated APIs: pass next_cursor back as `cursor` to get the next page
                nxt = from_headers(result["next_cursor"], headers) if result["next_cursor"].startswith(("link:", "header:")) else _dig(data, result["next_cursor"])
                out["next_cursor"] = str(nxt) if nxt not in (None, "", False) else None
                if out["next_cursor"] is not None and args.get("cursor") not in (None, "") and out["next_cursor"] == str(args["cursor"]):
                    out["next_cursor"] = None  # the platform handed back the cursor it was given: following it would loop forever
                if result.get("trim"):
                    # the platform ignores the page size (fixed pages): return `limit` rows and a cursor to the rest of
                    # this upstream page first, then to the next upstream page
                    limit = min(limit, int(tool.get("max_limit", 100)))
                    out[result.get("key", "items")] = items[skip:skip + limit]
                    if skip + limit < len(items):
                        out["next_cursor"] = encode_cursor(used_cursor, skip + limit)
                out["next_page"] = None if out["next_cursor"] is None else out["next_page"]
            return out
        if "fields" in result:
            record = _dig(data, arg_path(result.get("root")))
            if not isinstance(record, dict) or not record:
                fields = result["fields"]
                if fields and all(isinstance(v, str) and v.startswith("=") for v in fields.values()):
                    return _map_fields({}, fields, args)  # a write that answers 204/empty: the literals are the result
                if read:  # a read verb (GraphQL and SOAP reads are POSTs): the record does not exist
                    raise NotFound("platform returned no record", status=404)
                raise InvalidInput("platform returned no record", status=404)
            return _map_fields(record, result["fields"], args)
        return {"raw": data}

    def _is_read(self, verb: str, tool: dict) -> bool:
        """Read or write by the vocabulary (a GraphQL or SOAP read is a POST); the HTTP method when the verb is unknown."""
        try:
            from .vocab import vocab_for
            return bool(vocab_for(self.spec)[verb]["read_only"])
        except Exception:  # noqa: BLE001 - no vocabulary at hand: fall back to the method
            return tool.get("method", "GET").upper() == "GET"

    async def _request(self, tool: dict, args: dict, cache_ttl: float | None = None, want_headers: bool = False, read: bool | None = None) -> Any:
        tool = {**tool, "_creds": self.transport.creds}
        params: dict[str, Any] = {}
        for api_name, expr in tool.get("params", {}).items():
            params[api_name] = self._value(expr, args, tool)
        for k, v in tool.get("fixed_params", {}).items():
            params[k] = v
        path = tool["path"]
        path_params = tool.get("path_params", {})  # fallback expressions for path variables (e.g. page, =literal)
        auth = self.spec["adapter"].get("auth", {})
        for var in _PATH_VAR.findall(path):
            if (auth.get("type") == "path" and var == auth.get("field", "token")) or (var == "access_token" and var not in args):
                continue  # the transport fills the credential / minted-token placeholder
            value = args.get(var)
            if value in (None, "") and var in path_params:
                value = self._value(path_params[var], args, tool)
            if value in (None, ""):
                raise InvalidInput(f"missing argument {var!r}" + (f" (built from {path_params[var]!r}: give the arguments it reads)" if var in path_params else ""))
            path = path.replace("{" + var + "}", encode_path_value(value))  # no query, fragment or dot segments from an argument
        body = None
        if tool.get("body"):
            # keys that all start with an index build a top-level array body ([{...}], Pinterest PATCH)
            body = [] if all(_split_key(k)[0].isdigit() for k in tool["body"]) else {}
            for k, expr in tool["body"].items():
                v = self._value(expr, args, tool)
                if v is None:
                    continue
                if "{" in k:  # a key built from an argument: "updates.{item_id}.quantity"
                    k = _PATH_VAR.sub(lambda m: str(self._value(m.group(1), args, tool)), k)
                # dotted keys build nested objects, digit segments build arrays:
                # "article.title" -> {"article": {"title": v}}; "to.0.email" -> {"to": [{"email": v}]}
                _set_path(body, _split_key(k), v)
        return await self.transport.request(
            tool.get("method", "GET"), path, params=params, json=body, form=tool.get("body_format") == "form",
            xml_root=tool.get("xml_root") if tool.get("body_format") == "xml" else None, multipart=tool.get("body_format") == "multipart",
            headers=tool.get("headers"), query_safe=tool.get("query_safe", ""), sign=tool.get("sign", True), cache_ttl=cache_ttl,
            csv=tool.get("csv"), **({"want_headers": True} if want_headers else {}), **({"read": read} if read is not None else {}),
        )

    @staticmethod
    def _value(expr: Any, args: dict, tool: dict) -> Any:
        """A param expression is an argument name, or a small formula: ``offset`` (derived from
        page/limit), ``limit`` with the platform's cap, or a literal ``=value``."""
        if isinstance(expr, str) and expr.startswith("="):
            return expr[1:]
        if isinstance(expr, str) and expr.startswith("json:"):
            # a typed literal (boolean, number, object, array) for APIs that reject strings
            import json as _json
            return _json.loads(expr[5:])
        if isinstance(expr, str) and expr.startswith("str:"):
            # coerce an argument to a string (APIs that document numeric fields as strings)
            inner = Adapter._value(expr[4:], args, tool)
            if isinstance(inner, float):
                from decimal import Decimal
                text = format(Decimal(repr(inner)), "f")  # never scientific notation (5e-05 → 0.00005)
                return text.rstrip("0").rstrip(".") if "." in text else text
            return None if inner is None else str(inner)
        if isinstance(expr, str) and expr.startswith("jsonstr:"):
            # jsonstr:{"text":{text}} — a JSON document serialized to a string; each {expr} becomes a JSON value
            import json as _json
            import re as _re
            missing = []

            def sub(m):
                v = Adapter._value(m.group(1), args, tool)
                if v is None:
                    missing.append(m.group(1))
                return _json.dumps(v, ensure_ascii=False)
            text = _re.sub(r"\{([A-Za-z_@][A-Za-z0-9_.:@]*)\}", sub, expr[8:])
            if missing:
                return None
            return _json.dumps(_json.loads(text), ensure_ascii=False, separators=(",", ":"))
        if isinstance(expr, str) and expr.startswith("fmt:"):
            # fmt:customers/{@customer_id}/campaigns/{campaign_id} — each {expr} is any expression
            import re as _re
            missing = []

            def sub(m):
                v = Adapter._value(m.group(1), args, tool)
                if v is None or v == "":
                    missing.append(m.group(1))
                    return ""
                return str(v)

            def piece(m):
                if m.group(2) is not None:
                    return sub(_re.match(r"\{([^{}]+)\}", m.group(0)))
                # [?optional part]: a group written [?...] holding an {expr} is left out when any of its expressions is
                # missing (Treasury filter=security_desc:eq:{series_id}[?,record_date:gte:{start}]); one pass, so a
                # value containing braces is never expanded again
                before = len(missing)
                text = _re.sub(r"\{([^{}]+)\}", sub, m.group(1))
                if len(missing) > before:
                    del missing[before:]
                    return ""
                return text
            out = _re.sub(r"\[\?([^\[\]{}]*(?:\{[^{}]+\}[^\[\]{}]*)+)\]|\{([^{}]+)\}", piece, expr[4:])
            return None if missing else out
        if isinstance(expr, str) and expr.startswith("date:"):
            # date:<expr> — the value only if it is exactly an ISO date (safe to splice into a query language)
            v = Adapter._value(expr[5:], args, tool)
            if v in (None, ""):
                return None
            import re as _re
            if not _re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(v)):
                raise InvalidInput(f"{expr[5:]!r} must be an ISO date (YYYY-MM-DD), got {v!r}")
            return str(v)
        if isinstance(expr, str) and expr.startswith(("year:", "month:", "day:")):
            # year:/month:/day:<expr> — integer part of an ISO date (Rest.li dateRange)
            part, _, inner = expr.partition(":")
            v = Adapter._value(inner, args, tool)
            if v in (None, ""):
                return None
            import re as _re
            m = _re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(v))
            if not m:
                raise InvalidInput(f"{inner!r} must be an ISO date (YYYY-MM-DD), got {v!r}")
            return int(m.group({"year": 1, "month": 2, "day": 3}[part]))
        if isinstance(expr, str) and expr.startswith("map:"):
            # map:<expr>:pause=PAUSED,resume=ENABLED — translate a vocabulary enum to the platform's value
            body = expr[4:]
            cut = body.rfind(":", 0, body.find("=") if "=" in body else len(body))  # table starts after the last ':' before the first '='
            inner, table = body[:cut], body[cut + 1:]
            pairs = dict(item.split("=", 1) for item in table.split(",") if "=" in item)
            value = Adapter._value(inner, args, tool)
            if value is None:
                return None
            if str(value) not in pairs:
                raise InvalidInput(f"{inner!r} must be one of {sorted(pairs)}, got {value!r}")
            out = pairs[str(value)]
            if out.startswith("json:"):  # typed target: map:action:pause=json:false,resume=json:true
                import json as _json
                return _json.loads(out[5:])
            return out
        if isinstance(expr, str) and expr.startswith("int:"):
            # coerce an argument or config value to an integer (ids typed as numbers)
            inner = Adapter._value(expr[4:], args, tool)
            if inner is None or inner == "":
                return None
            try:
                if isinstance(inner, float) and not inner.is_integer():
                    raise ValueError(inner)  # never truncate (12.5 → 12 would silently change a budget)
                return int(inner) if not isinstance(inner, str) else int(inner.strip())
            except (TypeError, ValueError):
                raise InvalidInput(f"{expr[4:]!r} must be an integer, got {inner!r}")
        if isinstance(expr, str) and expr.startswith(("epoch:", "epoch_ms:")):
            # epoch seconds / milliseconds of an ISO date or datetime (or of another expression)
            kind, _, inner = expr.partition(":")
            v = Adapter._value(inner, args, tool)
            if v in (None, ""):
                return None
            t = _parse_when(v).timestamp()
            return int(t * 1000) if kind == "epoch_ms" else int(t)
        if expr in ("now_epoch", "now_epoch_ms"):
            import time as _time
            return int(_time.time() * 1000) if expr == "now_epoch_ms" else int(_time.time())
        if expr == "today":
            from datetime import datetime, timezone
            return datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if isinstance(expr, str) and expr.startswith(("days_ago:", "days_ahead:")):
            # an ISO date N days before/after today (UTC): default report windows, required end dates
            from datetime import datetime, timedelta, timezone
            kind, _, n = expr.partition(":")
            delta = timedelta(days=int(n))
            d = datetime.now(timezone.utc) + (delta if kind == "days_ahead" else -delta)
            return d.strftime("%Y-%m-%d")
        if isinstance(expr, str) and expr.startswith("datefmt:"):
            # datefmt:<pattern>:<expr> — reformat a date (%Y %y %m %d %H %M %S), e.g. datefmt:%m/%d/%Y:date_from
            rest = expr[8:]
            cut = rest.find(":", rest.rfind("%") + 2) if "%" in rest else rest.find(":")
            pattern, inner = rest[:cut], rest[cut + 1:]
            v = Adapter._value(inner, args, tool)
            if v in (None, ""):
                return None
            from datetime import timezone as _tz
            return _fmt_when(pattern, _parse_when(v).astimezone(_tz.utc))  # UTC, as the TypeScript runtime formats
        if isinstance(expr, str) and expr.startswith(("minor:", "micros:", "mul:")):
            # money in minor units: minor:price (×100), micros:budget (×1e6), mul:<factor>:<expr>
            from decimal import ROUND_HALF_UP, Decimal
            if expr.startswith("mul:"):
                _, factor, inner = expr.split(":", 2)
            else:
                factor, inner = ("100" if expr.startswith("minor:") else "1000000"), expr.split(":", 1)[1]
            v = Adapter._value(inner, args, tool)
            if v in (None, ""):
                return None
            try:
                return int((Decimal(str(v)) * Decimal(factor)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            except Exception:
                raise InvalidInput(f"{inner!r} must be a number, got {v!r}")
        if isinstance(expr, str) and expr.startswith("part:"):
            # part:<n>:<expr> — the n-th (0-based) '/'-separated part of a value: a two-dimensional series id
            # "USA/NY.GDP.MKTP.CD" fills /country/{country}/indicator/{indicator}; a missing part is absent
            _, n, inner = expr.split(":", 2)
            v = Adapter._value(inner, args, tool)
            if v in (None, ""):
                return None
            parts = str(v).split("/")
            return parts[int(n)] if int(n) < len(parts) and parts[int(n)] != "" else None
        if expr == "cursor":
            return args.get("cursor") or None
        if isinstance(expr, str) and expr.startswith("jsonpart:"):
            # a multipart part sent as application/json: jsonpart:json:{...} or jsonpart:<arg>
            v = Adapter._value(expr[9:], args, tool)
            return {"_json_part": v} if v is not None else None
        if isinstance(expr, str) and expr.startswith("file:"):
            # a file part for multipart bodies, downloaded from a URL argument (image_urls.0, image_url)
            v = Adapter._value(expr[5:], args, tool)
            return {"_file_url": str(v)} if v not in (None, "") else None
        if expr == "offset":
            # the page size actually sent (capped by max_limit): an uncapped limit would skip rows between pages
            page = int(args.get("page") or 1)
            return (page - 1) * effective_limit(tool, args)
        if expr == "limit":
            return effective_limit(tool, args)
        if expr == "page":
            return int(args.get("page") or 1)
        if expr == "page0":
            return int(args.get("page") or 1) - 1
        if expr == "uuid":
            import uuid as _uuid
            return str(_uuid.uuid4())  # client-generated transaction / idempotency ids
        if expr == "now":
            from datetime import datetime, timezone
            return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        if isinstance(expr, str) and expr.startswith("@"):
            # a per-install config or credential field (sender address, contact e-mail, country)
            return tool.get("_creds", {}).get(expr[1:])
        if isinstance(expr, str) and "." in expr:
            return _dig(args, expr)  # an element of an array argument: image_urls.0
        return args.get(expr)
