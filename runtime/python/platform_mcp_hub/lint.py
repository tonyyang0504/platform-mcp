"""Catalog lint: the evidence and naming rules every served entry must satisfy (`platform-mcp-hub lint [--json] [entry.json ...]`).
Exit 1 on any error. Warnings do not fail."""
import json
import re
import sys
from pathlib import Path

from . import catalog as _catalog
from . import environment as _environment
from . import generic as _generic
from . import netguard as _netguard
from . import sanitize as _sanitize

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def lint_endpoints(a: dict) -> list[str]:
    """Every URL the runtime calls with credentials is https, and no catalog URL names this machine or a private
    network (a hostile doc could otherwise steer try_tool/live_verify, or an installed server, at internal hosts)."""
    from urllib.parse import urlsplit
    errs = []
    auth = a.get("auth") or {}
    urls = [("adapter.base_url", a.get("base_url"))]
    urls += [(f"tool {v}: path", t.get("path")) for v, t in (a.get("tools") or {}).items() if isinstance(t, dict) and isinstance(t.get("path"), str) and "://" in t["path"]]
    for key in ("token_url", "auth_url"):
        if auth.get(key):
            urls.append((f"auth.{key}", auth[key]))
    login = auth.get("login")
    if isinstance(login, dict) and isinstance(login.get("path"), str) and "://" in login["path"]:
        urls.append(("auth.login.path", login["path"]))
    for where, url in urls:
        if not isinstance(url, str):
            continue
        if not url.startswith("https://"):
            errs.append(f"{where} must be an https URL")
            continue
        try:
            host = (urlsplit(url).hostname or "").lower()
        except ValueError:
            host = ""
        if "{" in url.split("/", 3)[2] or not host:
            continue  # a per-install host ({instance}) is the operator's choice
        literal = bool(re.fullmatch(r"[0-9.]+", host)) or ":" in host or host.startswith("0x")  # dotted, decimal, hex or IPv6 forms
        if host == "localhost" or host.endswith(".localhost") or (literal and not _netguard.is_public_ip(host)):
            errs.append(f"{where} names a loopback/private/link-local host ({host}); catalog endpoints must be public")
    return errs
VOCAB = _catalog.vocab()
NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,60}$")
LIVE_STATUSES = {"working", "degraded", "broken", "blocked", "needs_credentials"}
AUTH_TYPES = {"none", "bearer", "header", "basic", "query", "path", "session", "oauth2_client_credentials", "oauth2_refresh_token"}
# the adapter expression language (CONTRIBUTING.md "Adapter contract"); both runtimes implement exactly these
EXPR_KEYWORDS = {"offset", "limit", "page", "page0", "cursor", "now", "uuid", "now_epoch", "now_epoch_ms", "today"}
EXPR_PREFIXES = ("json:", "str:", "int:", "jsonstr:", "fmt:", "date:", "year:", "month:", "day:", "map:", "epoch:", "epoch_ms:",
                 "days_ago:", "days_ahead:", "datefmt:", "minor:", "micros:", "mul:", "jsonpart:", "file:", "part:")
_UNARY = ("str:", "int:", "date:", "year:", "month:", "day:", "epoch:", "epoch_ms:", "jsonpart:", "file:", "minor:", "micros:")


def expr_refs(expr) -> list[tuple[str, str]]:
    """What an adapter expression reads: ("arg", name) for a tool argument, ("field", name) for an
    @credential/config field. Mirrors Adapter._value in the runtimes."""
    if not isinstance(expr, str) or expr == "" or expr.startswith(("=", "json:")) or expr in EXPR_KEYWORDS:
        return []
    if expr.startswith(("days_ago:", "days_ahead:")):
        return []
    if expr.startswith("jsonstr:"):
        return [r for inner in re.findall(r"\{([A-Za-z_@][A-Za-z0-9_.:@]*)\}", expr[8:]) for r in expr_refs(inner)]
    if expr.startswith("fmt:"):
        return [r for inner in re.findall(r"\{([^{}]+)\}", expr[4:]) for r in expr_refs(inner)]
    if expr.startswith("map:"):
        body = expr[4:]
        cut = body.rfind(":", 0, body.find("=") if "=" in body else len(body))
        return expr_refs(body[:cut])
    if expr.startswith("datefmt:"):
        rest = expr[8:]
        cut = rest.find(":", rest.rfind("%") + 2) if "%" in rest else rest.find(":")
        return expr_refs(rest[cut + 1:])
    if expr.startswith(("mul:", "part:")):
        parts = expr.split(":", 2)
        return expr_refs(parts[2]) if len(parts) == 3 else []
    for pre in _UNARY:
        if expr.startswith(pre):
            return expr_refs(expr[len(pre):])
    if expr.startswith("@"):
        return [("field", expr[1:])]
    return [("arg", expr.split(".")[0])]


def _known_fields(a: dict) -> set:
    auth = a.get("auth") or {}
    names = {f.get("name") for f in auth.get("fields") or [] if isinstance(f, dict)}
    names |= {f.get("name") for f in a.get("config_fields") or [] if isinstance(f, dict)}
    for k, v in auth.items():
        if k.endswith("_field") and isinstance(v, str):
            names.add(v)
    if a.get("user_agent_field"):
        names.add(a["user_agent_field"])
    return {n for n in names if n}


TOOL_KEYS = {"body", "body_format", "cache_ttl", "csv", "default_limit", "docs", "fixed_params", "headers", "kind", "max_limit", "method",
             "note", "params", "path", "path_params", "query_safe", "result", "sign", "xml_root"}
RESULT_KEYS = {"cap", "columnar", "fields", "filter", "items", "items_are_values", "key", "next_cursor", "require", "root",
               "scalar_rows", "slice", "sort", "total", "trim"}
ENVELOPE_KEYS = {"error_field", "fail_if_present", "fail_when", "ok_field", "ok_value"}


def lint_envelope(env) -> list[str]:
    if env is None:
        return []
    if not isinstance(env, dict):
        return ["adapter.envelope must be an object"]
    errs = [f"adapter.envelope: unknown key {k!r} (known: {', '.join(sorted(ENVELOPE_KEYS))})" for k in sorted(set(env) - ENVELOPE_KEYS)]
    fip = env.get("fail_if_present")
    if fip is not None and not (isinstance(fip, list) and fip and all(isinstance(x, str) and x for x in fip)):
        errs.append("adapter.envelope.fail_if_present must be a non-empty list of dotted paths")
    if env.get("fail_when") is not None and not isinstance(env["fail_when"], dict):
        errs.append("adapter.envelope.fail_when must be an object {dotted path: value}")
    return errs


def lint_tool_refs(cat: str, verb: str, t: dict, a: dict, voc: dict | None = None) -> list[str]:
    """Every argument an expression or a path placeholder names must be an input of the verb (the
    servers drop anything else, so a typo silently sends nothing), every @field a declared field.
    `voc` is the entry's own tool definitions for a generic entry (generic.py)."""
    errs = []
    generic = voc is not None
    voc = voc if voc is not None else VOCAB.get(cat, {})
    inputs = set(((voc.get(verb) or {}).get("input") or {}).get("properties") or {})
    fields = _known_fields(a)
    exprs = []
    for key in ("params", "body", "path_params"):
        section = t.get(key) or {}
        if not isinstance(section, dict):
            errs.append(f"tool {verb}: {key} must be an object")
            continue
        for k, v in section.items():
            exprs.append((f"{key}.{k}", v))
            for inner in re.findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", k):
                exprs.append((f"{key} key {k}", inner))
    for where, expr in exprs:
        for kind, name in expr_refs(expr):
            if kind == "arg" and name not in inputs:
                errs.append(f"tool {verb}: {where} reads argument {name!r}, which is not an input of {cat}.{verb} (inputs: {', '.join(sorted(inputs)) or 'none'}); use an expression, =literal or @field")
            if kind == "field" and name not in fields:
                errs.append(f"tool {verb}: {where} reads @{name}, which is not a declared credential or config field")
    auth = a.get("auth") or {}
    for var in re.findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", str(t.get("path", ""))):
        if var in inputs or var in (t.get("path_params") or {}) or var in fields or var == "access_token" or var == auth.get("field"):
            continue
        errs.append(f"tool {verb}: path placeholder {{{var}}} is neither an input of {cat}.{verb}, a path_params entry nor a credential/config field")
    r = t.get("result") or {}
    if generic:
        return errs  # generic tools: their keys and result options are checked by generic.lint_tools
    # keys the runtimes read: anything else is a typo the servers would silently ignore ("item", "slices")
    for k in sorted(set(t) - TOOL_KEYS):
        errs.append(f"tool {verb}: unknown key {k!r} (known: {', '.join(sorted(TOOL_KEYS))})")
    if not isinstance(r, dict):
        errs.append(f"tool {verb}: result must be an object")
        return errs
    for k in sorted(set(r) - RESULT_KEYS):
        errs.append(f"tool {verb}: unknown result key {k!r} (known: {', '.join(sorted(RESULT_KEYS))})")
    csv = t.get("csv")
    if csv is not None and not (isinstance(csv, dict) and set(csv) <= {"delimiter", "skip_lines"}
                                and (csv.get("delimiter") is None or (isinstance(csv["delimiter"], str) and len(csv["delimiter"]) == 1))
                                and (csv.get("skip_lines") is None or (isinstance(csv["skip_lines"], int) and not isinstance(csv["skip_lines"], bool) and csv["skip_lines"] >= 0))):
        errs.append(f"tool {verb}: csv must be {{delimiter: one character, skip_lines: integer >= 0}}")
    if "cap" in r and r["cap"] not in ("head", "tail"):
        errs.append(f"tool {verb}: result.cap must be head or tail")
    if "cap" in r and r.get("slice"):
        errs.append(f"tool {verb}: result.cap and result.slice exclude each other (slice already pages locally)")
    for where in ("items", "root"):
        for name in re.findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", str(r.get(where) or "")):
            if name not in inputs:
                errs.append(f"tool {verb}: result.{where} names argument {{{name}}}, which is not an input of {cat}.{verb}")
    if not isinstance(r.get("fields", {}), dict):
        errs.append(f"tool {verb}: result.fields must be an object of normalised name -> source string")
    for norm, src in (r.get("fields") or {}).items() if isinstance(r.get("fields"), dict) else []:
        if not isinstance(src, str) or not src:
            errs.append(f"tool {verb}: result.fields.{norm} must be a non-empty string (a dotted path such as \"1\" or \"num:1\", =literal, ...), got {src!r}")
            continue
        if not src.startswith(("=", "fmt:")):
            for name in re.findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", src):
                if name not in inputs:
                    errs.append(f"tool {verb}: result.fields.{norm} names argument {{{name}}} in its path, which is not an input of {cat}.{verb}")
        if isinstance(src, str) and src.startswith("arg:") and src[4:] not in inputs:
            errs.append(f"tool {verb}: result.fields.{norm} echoes argument {src[4:]!r}, which is not an input of {cat}.{verb}")
    flt = r.get("filter")
    for i, rule in enumerate(flt if isinstance(flt, list) else [] if flt is None else [None]):
        if not isinstance(rule, dict) or not isinstance(rule.get("arg"), str):
            errs.append(f"tool {verb}: result.filter must be a list of {{arg, fields, match, value}} objects")
            break
        if rule["arg"] not in inputs:
            errs.append(f"tool {verb}: result.filter[{i}] filters on argument {rule['arg']!r}, which is not an input of {cat}.{verb}")
        if rule.get("match", "contains") not in ("contains", "equals", "gte", "lte"):
            errs.append(f"tool {verb}: result.filter[{i}].match must be contains, equals, gte or lte")
        if "fields" in rule and not (isinstance(rule["fields"], list) and rule["fields"] and all(isinstance(f, str) for f in rule["fields"])):
            errs.append(f"tool {verb}: result.filter[{i}].fields must be a non-empty list of normalised field paths")
        for kind, name in expr_refs(rule.get("value")):
            if kind == "arg" and name not in inputs:
                errs.append(f"tool {verb}: result.filter[{i}].value reads argument {name!r}, which is not an input of {cat}.{verb}")
    paged_verb = bool({"page", "cursor"} & inputs)
    if r.get("filter") and not r.get("slice") and paged_verb:
        errs.append(f"tool {verb}: result.filter on a paged verb needs result.slice (a whole collection paged locally); a server-paged list would lose rows")
    if r.get("trim") and not r.get("next_cursor"):
        errs.append(f"tool {verb}: result.trim needs result.next_cursor (it pages inside a fixed-size cursor page)")
    if r.get("trim") and r.get("slice"):
        errs.append(f"tool {verb}: result.trim and result.slice exclude each other")
    spec_v = VOCAB.get(cat, {}).get(verb) or {}
    if "cache_ttl" in t:
        if not isinstance(t["cache_ttl"], (int, float)) or isinstance(t["cache_ttl"], bool) or t["cache_ttl"] < 0 or t["cache_ttl"] > 3600:
            errs.append(f"tool {verb}: cache_ttl must be a number of seconds between 0 and 3600")
        elif t["cache_ttl"] and (not spec_v.get("read_only") or t.get("method", "GET") not in ("GET", "POST")):
            errs.append(f"tool {verb}: cache_ttl is only allowed on read tools (a write must never be answered from a cache)")
    if "items" in r:
        out = (VOCAB.get(cat, {}).get(verb) or {}).get("output") or {}
        lists = [k for k, sch in (out.get("properties") or {}).items() if isinstance(sch, dict) and sch.get("type") == "array" and isinstance(sch.get("items"), dict) and sch["items"].get("type") == "object"]
        if lists and r.get("key", "items") not in lists:
            errs.append(f"tool {verb}: result.key must be {lists[0]!r} (the {cat}.{verb} list), got {r.get('key', 'items')!r}")
    return errs


def lint(path: Path) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    try:
        e = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"no such file {path}"], []
    except ValueError as exc:
        return [f"not valid JSON: {exc}"], []
    if not isinstance(e, dict):
        return ["an entry must be a JSON object"], []
    pid, cat = e.get("id"), e.get("category")
    if not pid or path.stem != pid:
        errors.append("id must match the file name")
    label = e.get("label")
    if label is not None and (not isinstance(label, str) or any(ord(c) < 32 or ord(c) == 127 or c in "\u2028\u2029" for c in label)):
        errors.append("label must be one line of text without control characters (it is written into generated source)")
    # text a client's model reads as tool documentation (label in the title, instructions, tool notes): sanitize.py
    for key, kind in (("label", "label"), ("instructions", "instructions")):
        errors += [f"{key} {p}" for p in _sanitize.problems(e.get(key), kind)]
    for verb, t in ((e.get("adapter") or {}).get("tools") or {}).items() if isinstance(e.get("adapter"), dict) else ():
        if isinstance(t, dict):
            errors += [f"tool {verb}: note {p}" for p in _sanitize.problems(t.get("note"), "note")]
    if e.get("version") is not None and (not isinstance(e["version"], str) or not VERSION_RE.match(e["version"])):
        errors.append("version must be MAJOR.MINOR.PATCH (it is written into package metadata)")
    errors += lint_live_check(e, e.get("live_check"), "live_check")
    if "adapter" not in e:
        return errors, warnings
    if not isinstance(e["adapter"], dict):
        errors.append("adapter must be an object (a status-only entry omits it and sets adapter_status + reason)")
        return errors, warnings
    if path.parent.name != cat:
        errors.append(f"category {cat!r} does not match the directory {path.parent.name!r}")
    is_generic = cat == _generic.CATEGORY
    if not is_generic and cat not in VOCAB:
        errors.append(f"category {cat!r} has no vocabulary (or use \"generic\": tools defined by the API's own operations)")
        return errors, warnings
    voc = _generic.vocab(e) if is_generic else VOCAB[cat]
    a = e["adapter"]
    if not str(a.get("base_url", "")).startswith("https://"):
        errors.append("adapter.base_url must be https")
    errors += [e_ for e_ in lint_endpoints(a) if e_ != "adapter.base_url must be an https URL"]
    if not e.get("docs_url"):
        errors.append("docs_url required for a served platform")
    if not e.get("verified_at"):
        warnings.append("verified_at missing")
    elif not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(e["verified_at"])):
        errors.append("verified_at must be YYYY-MM-DD")
    if not e.get("version"):
        warnings.append("version missing (add \"version\": \"0.1.0\")")
    for verb in a.get("not_offered") or {}:
        if verb in (a.get("tools") or {}):
            errors.append(f"verb {verb!r} is both mapped and under not_offered")
        elif not is_generic and verb not in voc:
            warnings.append(f"not_offered names {verb!r}, which is not a {cat} verb")
    auth = a.get("auth", {"type": "none"})
    if auth.get("type", "none") not in AUTH_TYPES:
        errors.append(f"unsupported auth type {auth.get('type')!r}")
    for f in auth.get("fields", []):
        if isinstance(f, dict) and not f.get("help"):
            warnings.append(f"credential field {f.get('name')} has no help text")
    if not isinstance(a.get("tools"), dict) or not a["tools"]:
        errors.append("adapter.tools must be a non-empty object")
        return errors, warnings
    errors += lint_envelope(a.get("envelope"))
    if is_generic:
        errors += _generic.lint_tools(e)
    for verb, t in a["tools"].items():
        if not is_generic and verb not in voc:
            errors.append(f"tool {verb!r} is not in the {cat} vocabulary")
        if not NAME_RE.match(verb):
            errors.append(f"tool name {verb!r} violates [A-Za-z0-9_.-]{{1,60}}")
        if not isinstance(t, dict):
            errors.append(f"tool {verb}: must be an object")
            continue
        if not isinstance(t.get("path"), str) or (t["path"] and not t["path"].startswith(("/", "https://", "?"))):
            # "" posts to base_url itself (a SOAP endpoint, a GraphQL or JSON-RPC URL)
            errors.append(f"tool {verb}: path required (a string starting with '/', 'https://' or '?', or \"\" for base_url itself)")
        if not (t.get("docs") or e.get("docs_url")):
            errors.append(f"tool {verb}: docs link required")
        if t.get("method", "GET") not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            errors.append(f"tool {verb}: bad method")
        if is_generic:
            errors += lint_tool_refs(cat, verb, t, a, voc)
            for key, kind in (("description", "note"), ("title", "label")):
                errors += [f"tool {verb}: {key} {p}" for p in _sanitize.problems(t.get(key), kind)]
            errors += [f"tool {verb}: input {p}" for p in _schema_text_problems(t.get("input"))]
            continue
        if verb in voc:
            errors += lint_tool_refs(cat, verb, t, a)
        r = t.get("result", {})
        if "items" in r and "fields" not in r:
            warnings.append(f"tool {verb}: list result without field mapping")
        for k in r.get("fields", {}):
            allowed = set(VOCAB[cat][verb]["output"].get("properties", {}))
            item = VOCAB[cat][verb]["output"].get("properties", {}).get(r.get("key", "items"), {}).get("items", {}).get("properties", {}) if "items" in r else {}
            if k not in allowed and k not in item:
                warnings.append(f"tool {verb}: mapped field {k!r} is not in the output schema")
    for verb in ([] if is_generic else voc):
        if verb not in a["tools"] and verb not in a.get("not_offered", {}):
            warnings.append(f"verb {verb} neither offered nor explained under not_offered")
    for text in json.dumps(a).splitlines():
        if re.search(r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*[\"']?[A-Za-z0-9]{16,}", text):
            errors.append("possible secret literal in adapter block")
    errors += lint_error_kinds(a)
    errors += lint_auth_audit(e, e.get("auth_audit"), "auth_audit")
    errors += _environment.lint(a)
    errors += lint_environment_checks(e)
    return errors, warnings


def _schema_text_problems(schema, path: str = "") -> list[str]:
    """Descriptions and titles inside a generic tool's input schema reach the client's model too."""
    out = []
    if isinstance(schema, dict):
        for k, v in schema.items():
            if k in ("description", "title") and isinstance(v, str):
                out += [f"{path or 'schema'}.{k} {p}" for p in _sanitize.problems(v, "note")]
            else:
                out += _schema_text_problems(v, f"{path}.{k}" if path else k)
    elif isinstance(schema, list):
        for i, v in enumerate(schema):
            out += _schema_text_problems(v, f"{path}[{i}]")
    return out


def lint_live_check(e: dict, lc, where: str) -> list[str]:
    """`live_check` is written by platform-mcp-hub verify --record: {date, status, egress, notes}."""
    if lc is None:
        return []
    errors = []
    if not isinstance(lc, dict) or set(lc) - {"date", "status", "egress", "notes"}:
        return [f"{where} must be an object with only date, status, egress, notes"]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(lc.get("date", ""))):
        errors.append(f"{where}.date must be YYYY-MM-DD")
    if lc.get("status") not in LIVE_STATUSES:
        errors.append(f"{where}.status must be one of {sorted(LIVE_STATUSES)}")
    if not isinstance(lc.get("egress"), str) or not lc.get("egress"):
        errors.append(f"{where}.egress must name where the calls left from")
    if not isinstance(lc.get("notes"), str):
        errors.append(f"{where}.notes must be a string")
    if "adapter" not in e:
        errors.append(f"{where} is only meaningful on a served entry (with an adapter)")
    return errors


def lint_environment_checks(e: dict) -> list[str]:
    """`environment_checks {env: {live_check, auth_audit}}`: live_verify.py / auth_audit.py results for a
    declared non-production environment (--env), kept apart from the production blocks."""
    ec = e.get("environment_checks")
    if ec is None:
        return []
    declared = (e.get("adapter") or {}).get("environments") or {}
    if not isinstance(ec, dict) or not ec:
        return ["environment_checks must be a non-empty object {environment: {live_check, auth_audit}}"]
    errs = []
    for name, block in ec.items():
        where = f"environment_checks.{name}"
        if name not in declared:
            errs.append(f"{where}: {name!r} is not declared under adapter.environments")
        if not isinstance(block, dict) or not block or set(block) - {"live_check", "auth_audit"}:
            errs.append(f"{where} must be an object with live_check and/or auth_audit")
            continue
        errs += lint_live_check(e, block.get("live_check"), f"{where}.live_check")
        errs += lint_auth_audit(e, block.get("auth_audit"), f"{where}.auth_audit")
    return errs


ERROR_KINDS = {"invalid_input", "not_found", "conflict", "auth_error", "rate_limited", "upstream_error"}


def lint_error_kinds(a: dict) -> list[str]:
    """adapter.error_kinds [{status, match, kind}]: per-entry overrides of the runtimes' error table."""
    rules = a.get("error_kinds")
    if rules is None:
        return []
    if not isinstance(rules, list) or not rules:
        return ["adapter.error_kinds must be a non-empty list of {status, match, kind} rules"]
    errs = []
    for i, rule in enumerate(rules):
        if not isinstance(rule, dict) or set(rule) - {"status", "match", "kind", "note"}:
            errs.append(f"adapter.error_kinds[{i}] must be an object with only status, match, kind, note")
            continue
        if rule.get("kind") not in ERROR_KINDS:
            errs.append(f"adapter.error_kinds[{i}].kind must be one of {sorted(ERROR_KINDS)}")
        st = rule.get("status")
        sts = st if isinstance(st, list) else [st] if st is not None else []
        if not all(isinstance(x, int) and not isinstance(x, bool) and (x == 200 or 400 <= x <= 599) for x in sts) or (isinstance(st, list) and not st):
            errs.append(f"adapter.error_kinds[{i}].status must be an HTTP error status (400-599), 200 for envelope failures, or a list of them")
        if "match" in rule and (not isinstance(rule["match"], str) or not rule["match"]):
            errs.append(f"adapter.error_kinds[{i}].match must be a non-empty string (case-insensitive substring of the body)")
        if st is None and "match" not in rule:
            errs.append(f"adapter.error_kinds[{i}] needs a status or a match (it would reclassify every failure)")
    return errs


AUTH_AUDIT_STATUSES = {"verified_live", "spec_conformant", "reachable_unverified", "mismatch", "broken", "blocked"}


_FROM_ENTRY = object()


def lint_auth_audit(e: dict, au=_FROM_ENTRY, where: str = "auth_audit") -> list[str]:
    """`auth_audit` is written by tools/auth_audit.py apply: {date, status, evidence[], notes} on served
    entries whose adapter needs credentials (docs/AUTH_AUDIT.md); `au`/`where` check an environment's copy."""
    if au is _FROM_ENTRY:
        au = e.get("auth_audit")
    if au is None:
        return []
    errs = []
    if not isinstance(au, dict) or set(au) - {"date", "status", "evidence", "notes"}:
        return [f"{where} must be an object with only date, status, evidence, notes"]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(au.get("date", ""))):
        errs.append(f"{where}.date must be YYYY-MM-DD")
    if au.get("status") not in AUTH_AUDIT_STATUSES:
        errs.append(f"{where}.status must be one of {sorted(AUTH_AUDIT_STATUSES)}")
    ev = au.get("evidence")
    if not isinstance(ev, list) or not ev or not all(isinstance(x, str) and x for x in ev):
        errs.append(f"{where}.evidence must be a non-empty list of strings")
    if not isinstance(au.get("notes"), str) or not au.get("notes"):
        errs.append(f"{where}.notes must be a non-empty string")
    if "adapter" not in e:
        errs.append(f"{where} is only meaningful on a served entry (with an adapter)")
    elif e["adapter"].get("auth", {}).get("type", "none") == "none":
        errs.append(f"{where} covers adapters that need credentials (auth.type != none)")
    return errs


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(_catalog.catalog_dir().parent))
    except ValueError:
        return str(p)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]
    paths = [Path(p) for p in argv] or sorted(_catalog.catalog_dir().glob("*/*.json"))
    total_err = 0
    served = 0
    report = {"errors": [], "warnings": []}
    for p in paths:
        if p.parent.name in ("schema", "sources") or p.name == "index.json":
            continue
        errors, warnings = lint(p)
        if not errors or p.exists():
            try:
                served += "adapter" in json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                pass
        for w in warnings:
            report["warnings"].append(f"{_rel(p)}: {w}")
        for err in errors:
            report["errors"].append(f"{_rel(p)}: {err}")
        total_err += len(errors)
    if as_json:
        print(json.dumps({**report, "entries": len(paths), "served": served}, ensure_ascii=False))
    else:
        for w in report["warnings"]:
            print(f"warning: {w}")
        for err in report["errors"]:
            print(f"error: {err}")
        print(f"linted {len(paths)} entries, {served} served, {total_err} errors")
    return 1 if total_err else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
