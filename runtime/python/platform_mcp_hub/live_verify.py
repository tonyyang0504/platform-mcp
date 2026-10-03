"""Live verification of served catalog entries against the real platforms, over stdio, exactly as
an MCP client runs them: spawn the server, initialize, tools/list, then call every READ tool with
realistic arguments (search -> get by an id from the search -> page 2), validate every result
against the vocabulary's output schema, check pagination advances, get(id) returns the same item,
a bad id is a clean tool error, and time each call. Write tools are never called.

Usage (the `mcp` client and `jsonschema` importable; `pip install platform-mcp-hub[verify]`):
    platform-mcp-hub verify [--only id,cat/id,...] [--entry my_entry.json] [--auth none] [--lang py|ts|both]
                            [--egress LABEL] [--json report.json] [--delay 1.0] [--record] [--env sandbox]
    platform-mcp-hub verify --from-json report.json --markdown docs/LIVE_VERIFICATION.md [--compare other.json]

Launch: every server is started as `python -m platform_mcp_hub serve --entry <file>` (this interpreter, this
package) and `node <cli.js> serve --entry <file>` for TypeScript (launch.py finds the TypeScript CLI).

Environments: --env <name> runs only the entries that declare adapter.environments.<name> and starts each
server with PLATFORM_MCP_<ID>_ENV=<name> (supply that environment's own credentials in the usual
PLATFORM_MCP_<ID>_* variables); --record then writes environment_checks.<name>.live_check instead of the
production live_check.

Politeness: calls run sequentially, at least --delay seconds apart and never faster than the
catalog's rate_per_second; a 429 Retry-After is honoured before the next call; nothing is retried.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as _dt
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

from . import catalog as _catalog
from . import generic as _generic
from . import launch

VOCAB = _catalog.vocab()
SOURCES: dict[str, Path] = {}  # "category/id" -> the entry file each server is started from (and --record writes)
BAD_ID = "zz-live-verify-nonexistent-000000"
STATUSES = ("working", "degraded", "broken", "blocked", "needs_credentials")

# Default search arguments per list verb; PLANS below override per platform.
DEFAULT_ARGS = {
    "search": {"query": "developer", "limit": 10},
    "search_postings": {"query": "software", "limit": 10},
    "search_listings": {"query": "toyota", "limit": 10},
    "discover": {"limit": 10},
    "list_products": {"query": "phone", "limit": 10},
    "search_symbols": {"query": "BTC", "limit": 10},
    "list_markets": {"query": "BTC", "limit": 10},
    "get_news": {"query": "bitcoin", "limit": 10},
    "list_campaigns": {"limit": 10},
    "list_orders": {},
    "list_accounts": {},
}
SALES_SEARCH = {"query": "bank", "limit": 10}

# detail verb -> (source list verbs, argument name, field of the list item that feeds it)
DETAIL = {
    "get_posting": (("search", "search_postings"), "id", "id"),
    "get_listing": (("search_listings",), "listing_id", "id"),
    "get_competition": (("discover",), "competition_id", "id"),
    "standings": (("discover",), "competition_id", "id"),
    "get_company": (("search",), "id", "id"),
    "get_product": (("list_products",), "id", "id"),
    "get_ticker": (("list_markets",), "symbol", "symbol"),
    "get_candles": (("search_symbols", "list_markets"), "symbol", "symbol"),
    "decode_vin": ((), "vin", "vin"),
}

def days_ago(n: int) -> str:
    return (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=n)).strftime("%Y-%m-%d")


# Per-platform plans: non-secret public config (a public job board's name), argument overrides per
# verb, fixed ids for detail tools with no list source, and verbs to leave out with a reason.
PLANS: dict[str, dict] = {
    "jobs/greenhouse": {"config": {"board_token": "gitlab"}, "args": {"search": {"query": "engineer"}}},
    "jobs/ashby": {"config": {"job_board_name": "ashby"}, "args": {"search": {"query": "engineer"}}},
    "jobs/lever": {"config": {"site": "palantir", "api_host": "api.lever.co"}, "args": {"search": {"query": "engineer"}}},
    "jobs/pinpoint": {"config": {"company_subdomain": "workwithus"}, "args": {"search": {"query": ""}}},
    "jobs/smartrecruiters": {"config": {"company_identifier": "BoschGroup"}, "args": {"search": {"query": "engineer"}}},
    "jobs/talentlyft": {"config": {"subdomain": "span"}, "args": {"search": {"query": ""}}},
    # SEC fair access requires the operator's real company name + e-mail in the User-Agent (403 without
    # one); live_verify never invents a contact, so this entry is verified only up to that clean refusal
    "sales/us_sec_edgar": {"ids": {"get_company": "0000320193"}},
    "sales/gleif_lei": {"args": {"search": {"query": "Deutsche Bank"}}},
    "sales/no_brreg": {"args": {"search": {"query": "equinor"}}},
    "jobs/hn_who_is_hiring": {"ids": {"get_posting": "hn:Ask HN: Who is hiring?"}},
    "deals/hacker_news_freelancer_seeking_freelancer": {"ids": {"get_posting": "hn:Ask HN: Freelancer? Seeking freelancer?|Ask HN: Who wants to be hired?"}},
    "social/hackernews": {"ids": {"analytics_post": "8863"}},
    "jobs/remotive": {"no_page2": "the API documents only limit (fetch at most ~4 times a day)"},
    "deals/remotive": {"no_page2": "the API documents only limit (fetch at most ~4 times a day)"},
    "market_data/binance_collector": {"args": {"search_symbols": {"query": "BTCUSDT"}, "get_candles": {"interval": "1h", "limit": 5}}},
    "market_data/binance_vision_collector": {"args": {"search_symbols": {"query": "BTCUSDT"}, "get_candles": {"interval": "1h", "limit": 5}}},
    "market_data/bybit_collector": {"args": {"search_symbols": {"query": "BTCUSDT"}, "get_candles": {"interval": "60", "limit": 5}}},
    "market_data/polymarket_collector": {"ids": {"get_series": "from:search_symbols:raw.clobTokenIds"},
                                         "args": {"get_series": {"start": str(int(time.time()) - 7 * 86400), "end": str(int(time.time()))}}},
    # a public, empty wallet: the account tools answer their empty shapes (never a real person's address)
    "trading/hyperliquid": {"config": {"wallet_address": "0x0000000000000000000000000000000000000000"}, "may_be_empty": ["list_orders"]},
    "trading/hyperliquid_spot": {"config": {"wallet_address": "0x0000000000000000000000000000000000000000"}, "may_be_empty": ["list_orders", "get_balances"]},
    "automotive/autostrefa_mx": {"args": {"search_listings": {"make": "Toyota", "limit": 10}}},
    "deals/ted_eu": {"args": {"search_postings": {"query": 'FT~"software"', "limit": 10}}},
    "deals/bloggingpro_jobs": {"args": {"search_postings": {"query": "writer", "limit": 10}}},
    "competitions/topcoder": {"args": {"discover": {"status": "completed", "limit": 10}}},
    "jobs/problogger_jobs": {"args": {"search": {"query": "writer"}}},
    "deals/problogger_jobs": {"args": {"search_postings": {"query": "writer"}}},
    "deals/boamp": {"args": {"search_postings": {"query": "informatique", "limit": 10}}},
    "deals/tenderned": {"args": {"search_postings": {"limit": 10}}},
    "deals/kkj_go_jp": {"args": {"search_postings": {"query": "システム", "limit": 10}}},
    "deals/e_zamowienia": {"args": {"search_postings": {"limit": 10}}},
    "deals/pncp_pncp_gov_br": {"args": {"search_postings": {"limit": 10}}},
    "deals/etenders_etenders_gov_za": {"args": {"search_postings": {"limit": 10}}},
    "deals/uk_find_a_tender": {"args": {"search_postings": {"limit": 10}}},
    "deals/contracts_finder": {"args": {"search_postings": {"query": "software", "limit": 10}}},
    "deals/service_bund_de": {"args": {"search_postings": {"query": "Software", "limit": 10}}},
    "deals/world_bank_procurement": {"args": {"search_postings": {"query": "consulting", "limit": 10}}},
    # added through the forge end-to-end verification (docs/FORGE_VERIFICATION.md)
    "market_data/frankfurter": {"args": {"search_symbols": {"query": "dollar", "limit": 5}, "get_series": {"start": days_ago(10), "end": days_ago(1)}}, "ids": {"get_series": "USD"}},
    "trading/mercado_bitcoin": {"args": {"list_markets": {"query": "brl", "limit": 10}, "get_candles": {"interval": "1h", "limit": 5}}},
    "trading/bitstamp": {"args": {"list_markets": {"limit": 5}, "get_ticker": {"symbol": "btcusd"},
                                  "get_candles": {"symbol": "btcusd", "interval": "1h", "limit": 24}},
                         "ids": {"get_ticker": "btcusd"}},
    "trading/luno": {"args": {"list_markets": {"limit": 10}, "get_ticker": {"symbol": "XBTZAR"}}, "ids": {"get_ticker": "XBTZAR"}},
    "automotive/nhtsa_vpic": {"ids": {"decode_vin": "1HGCM82633A004352"}},
    "market_data/openfigi": {"args": {"search_symbols": {"query": "apple"}}},
    "competitions/codeforces": {"ids": {"get_competition": "566", "standings": "566"}},
    "trading/bitvavo": {"args": {"list_markets": {"query": "eur", "limit": 10}, "get_ticker": {"symbol": "BTC-EUR"},
                                 "get_candles": {"symbol": "BTC-EUR", "interval": "1h", "limit": 24}},
                        "ids": {"get_ticker": "BTC-EUR"}},
    "market_data/ecb_data_portal": {"ids": {"get_series": "EXR/D.USD.EUR.SP00.A"}, "args": {"get_series": {"start": days_ago(14), "end": days_ago(1)}}},
    # forge stress test 2026-10 (docs/FORGE_VERIFICATION.md "Stress test 2026-10")
    "trading/kraken": {"args": {"list_markets": {"query": "usd", "limit": 5}, "get_candles": {"interval": "1h", "limit": 5}}},
    "trading/gemini": {"args": {"list_markets": {"query": "usd", "limit": 5}, "get_candles": {"interval": "1hr", "limit": 5}}},
    "trading/kucoin": {"args": {"list_markets": {"query": "usdt", "limit": 5}, "get_candles": {"interval": "1h", "limit": 5}}},
    "trading/upbit": {"args": {"list_markets": {"query": "KRW", "limit": 5}, "get_candles": {"interval": "1h", "limit": 5}}},
    "trading/bitflyer": {"args": {"list_markets": {"query": "_", "limit": 3}}},
    "trading/coinbase_exchange": {"args": {"list_markets": {"query": "usd", "limit": 5}, "get_candles": {"interval": "1h", "limit": 5}}},
    "trading/kalshi": {"args": {"list_markets": {"limit": 5}}, "volatile": "open markets are listed newest first and change between the two runs"},
    "trading/dydx": {"args": {"list_markets": {"query": "usd", "limit": 5}, "get_candles": {"interval": "1h", "limit": 5}}},
    "trading/mexc": {"args": {"list_markets": {"query": "usdt", "limit": 5}, "get_candles": {"interval": "1h", "limit": 5}}},
    "trading/coinmate": {"args": {"list_markets": {"query": "_", "limit": 5}}},
    "market_data/coinpaprika": {"args": {"search_symbols": {"query": "bitcoin", "limit": 5}}},
    "market_data/us_treasury_fiscaldata": {"ids": {"get_series": "Treasury Bills"}, "args": {"get_series": {"start": days_ago(400)}}},
    "market_data/world_bank_indicators": {"ids": {"get_series": "USA/NY.GDP.MKTP.CD"}, "args": {"get_series": {"start": "2015-01-01", "end": "2024-12-31"}}},
    "market_data/bank_of_canada_valet": {"ids": {"get_series": "FXUSDCAD"}, "args": {"search_symbols": {"query": "exchange rate", "limit": 5}, "get_series": {"start": days_ago(30)}}},
    "market_data/cnb_fx": {"ids": {"get_series": "1 USD"}, "args": {"get_series": {"start": days_ago(10)}}},
    "market_data/bcb_sgs": {"ids": {"get_series": "433"}, "args": {"get_series": {"start": days_ago(400)}}},
    "market_data/cbr_dailyinfo": {"ids": {"get_series": "R01235"}, "args": {"search_symbols": {"query": "dollar", "limit": 3}, "get_series": {"start": days_ago(30), "end": days_ago(1)}}},
    "market_data/snb_data": {"ids": {"get_series": "devkum/M0/EUR1"}, "args": {"get_series": {"start": days_ago(400)}}},
    "market_data/nbp_rates": {"ids": {"get_series": "A/USD"}, "args": {"search_symbols": {"query": "dolar", "limit": 3}, "get_series": {"start": days_ago(60), "end": days_ago(1)}}},
    "market_data/federal_reserve_press": {"args": {"get_news": {"query": "", "limit": 5}}},
    "market_data/arxiv_qfin": {"args": {"get_news": {"query": "volatility", "limit": 5}}},
    "builder_tools/github_public": {"args": {"list_items": {"collection": "repositories", "query": "mcp server", "limit": 5}, "get_item": {"collection": "repositories"}},
                                    "ids": {"get_item": "modelcontextprotocol/servers"}},
    "builder_tools/gitlab_public": {"args": {"list_items": {"query": "mcp", "limit": 5}}, "ids": {"get_item": "from:list_items:id"}},
    "competitions/ctftime": {"args": {"discover": {"limit": 5}}, "ids": {"standings": "3335"}},
    "competitions/jolpica_f1": {"args": {"discover": {"limit": 5}}, "ids": {"get_competition": "2026/5", "standings": "2026/5"}},
    "competitions/openligadb": {"args": {"discover": {"query": "bundesliga", "limit": 5}}, "ids": {"standings": "bl1/2025"}},
    "deals/prozorro": {"args": {"search_postings": {"limit": 5}}, "volatile": "the tender feed is ordered by last modification and changes between the two runs"},
}


PLAN_KEYS = {"config", "args", "ids", "skip", "no_page2", "may_be_empty", "volatile"}


def hn_thread_kid(title_prefix: str) -> str:
    """The first comment of the latest monthly 'whoishiring' thread whose title starts with the prefix
    (official Firebase API: user -> submitted -> item -> kids)."""
    import httpx
    base = "https://hacker-news.firebaseio.com/v0"
    with httpx.Client(timeout=30, headers={"User-Agent": "platform-mcp live_verify"}) as c:
        items = []
        for sid in c.get(f"{base}/user/whoishiring.json").json().get("submitted", [])[:6]:
            time.sleep(1)
            items.append(c.get(f"{base}/item/{sid}.json").json() or {})
        for prefix in title_prefix.split("|"):  # alternatives, in order of preference
            for item in items:
                if str(item.get("title", "")).startswith(prefix) and item.get("kids"):
                    return str(item["kids"][0])
    raise RuntimeError(f"no whoishiring thread titled {title_prefix!r}")


def load_entries(auth: str | None, only: list[str] | None, env: str = "production", files: list[str] | None = None) -> list[dict]:
    out = []
    if files:
        paths = [Path(f).expanduser().resolve() for f in files]
    else:
        paths = [p for p in _catalog.entry_files() if p.name != "index.json"]
    for p in paths:
        d = json.loads(p.read_text(encoding="utf-8"))
        a = d.get("adapter")
        if not a:
            if files:
                raise SystemExit(f"{p}: no adapter block (only served entries can be verified)")
            continue
        key = f"{d['category']}/{d['id']}"
        if only and not any(o == key or o == d["id"] for o in only):
            continue
        if auth and (a.get("auth") or {}).get("type", "none") != auth:
            continue
        if env != "production" and env not in (a.get("environments") or {}):
            continue
        SOURCES[key] = p
        out.append(d)
    return out


def missing_credentials(entry: dict, config: dict) -> list[str]:
    a = entry["adapter"]
    pid = entry["id"]
    need = []
    for f in list((a.get("auth") or {}).get("fields") or []):
        if isinstance(f, dict) and f.get("required", True) and not os.environ.get(f"PLATFORM_MCP_{pid.upper()}_{f['name'].upper()}"):
            need.append(f["name"])
    return need


def missing_config(entry: dict, config: dict) -> list[str]:
    pid = entry["id"]
    return [f["name"] for f in entry["adapter"].get("config_fields") or []
            if f.get("required") and f["name"] not in config and not os.environ.get(f"PLATFORM_MCP_{pid.upper()}_{f['name'].upper()}")]


def entry_path(entry: dict) -> Path:
    key = f"{entry['category']}/{entry['id']}"
    return SOURCES.get(key) or (_catalog.catalog_dir() / entry["category"] / f"{entry['id']}.json")


def py_command(entry: dict) -> tuple[list[str], dict]:
    """`python -m platform_mcp_hub serve --entry <file>` with this interpreter and this package."""
    return launch.python_serve(entry_path(entry))


def ts_command(entry: dict, scratch: Path) -> tuple[list[str], dict]:
    """`node <platform-mcp-hub cli.js> serve --entry <file>` (launch.ts_cli finds the TypeScript CLI)."""
    return launch.ts_serve(entry_path(entry))


def schema_errors(verb_schema: dict, payload: Any) -> list[str]:
    from jsonschema import Draft202012Validator
    v = Draft202012Validator(verb_schema)
    return sorted({f"{'/'.join(str(p) for p in e.absolute_path) or '$'}: {e.message[:160]}" for e in v.iter_errors(payload)})[:8]


def list_key(verb_out: dict) -> str | None:
    for k, s in (verb_out.get("properties") or {}).items():
        if isinstance(s, dict) and s.get("type") == "array" and k not in ("skills", "tags", "images"):
            return k
    return None


def is_paginated(verb_in: dict) -> bool:
    props = verb_in.get("properties") or {}
    return "page" in props or "cursor" in props


def item_ids(items: list, field: str = "id") -> list:
    return [i.get(field) if isinstance(i, dict) else None for i in items]


class Runner:
    def __init__(self, delay: float, timeout: float):
        self.delay = delay
        self.timeout = timeout
        self.next_ok = 0.0

    async def wait(self, rate: float) -> None:
        gap = max(self.delay, 1.0 / rate if rate else 0)
        now = time.monotonic()
        if now < self.next_ok:
            await asyncio.sleep(self.next_ok - now)
        self.next_ok = time.monotonic() + gap

    async def call(self, session, name: str, args: dict, rate: float) -> dict:
        await self.wait(rate)
        t0 = time.monotonic()
        rec: dict[str, Any] = {"tool": name, "args": args}
        try:
            res = await asyncio.wait_for(session.call_tool(name, args), self.timeout)
            rec["latency_ms"] = int((time.monotonic() - t0) * 1000)
            rec["is_error"] = bool(res.is_error)
            rec["result"] = res.structured_content
            if res.is_error and isinstance(res.structured_content, dict):
                rec["error"] = res.structured_content.get("error")
                rec["message"] = str(res.structured_content.get("message", ""))[:300]
                rec["http_status"] = res.structured_content.get("http_status")
                ra = res.structured_content.get("retry_after_seconds")
                if ra:
                    self.next_ok = max(self.next_ok, time.monotonic() + min(float(ra), 300))
        except Exception as exc:  # protocol error, timeout, crash: exactly what we are looking for
            rec["latency_ms"] = int((time.monotonic() - t0) * 1000)
            rec["is_error"] = True
            rec["error"] = "client_exception"
            rec["message"] = f"{exc.__class__.__name__}: {exc}"[:300]
        return rec


def _blocked(rec: dict) -> bool:
    msg = (rec.get("message") or "").lower()
    return rec.get("http_status") == 403 or any(w in msg for w in ("captcha", "cloudflare", "access denied", "just a moment", "attention required"))


async def verify_server(entry: dict, lang: str, runner: Runner, scratch: Path, reuse: dict | None = None, env_name: str = "production") -> dict:
    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    key = f"{entry['category']}/{entry['id']}"
    plan = PLANS.get(key, {})
    config = plan.get("config", {})
    generic = _generic.is_generic(entry)
    vocab = _generic.vocab(entry) if generic else VOCAB[entry["category"]]
    rate = float(entry["adapter"].get("rate_per_second", 2) or 2)
    cmd, extra_env = py_command(entry) if lang == "py" else ts_command(entry, scratch)
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", "/tmp"), **extra_env}
    for k, v in os.environ.items():
        if k.startswith(f"PLATFORM_MCP_{entry['id'].upper()}_"):
            env[k] = v
    for name, value in config.items():
        env[f"PLATFORM_MCP_{entry['id'].upper()}_{name.upper()}"] = value
    if env_name != "production":
        env[f"PLATFORM_MCP_{entry['id'].upper()}_ENV"] = env_name  # the vendor environment under test
    out: dict[str, Any] = {"server": key, "lang": lang, "calls": [], "skipped": {}, "checks": {}, "may_be_empty": plan.get("may_be_empty", [])}
    creds = missing_credentials(entry, config)
    cfg = missing_config(entry, config)
    t0 = time.monotonic()

    class Session(ClientSession):
        async def validate_tool_result(self, name, result):  # we validate ourselves and record every error
            return None

    try:
        errlog = open(scratch / f"{entry['id']}.{lang}.stderr.log", "w")
        async with stdio_client(StdioServerParameters(command=cmd[0], args=cmd[1:], env=env), errlog=errlog) as (r, w):
            async with Session(r, w) as s:
                init = await asyncio.wait_for(s.initialize(), 60)
                tools = (await asyncio.wait_for(s.list_tools(), 60)).tools
                out["startup_ms"] = int((time.monotonic() - t0) * 1000)
                out["protocol"] = init.protocol_version
                out["tools"] = [t.name for t in tools]
                out["schemas"] = {t.name: {"in": t.input_schema, "out": t.output_schema, "read_only": bool(t.annotations and t.annotations.read_only_hint)} for t in tools}
                reads = [t.name for t in tools if t.annotations and t.annotations.read_only_hint]
                for t in tools:
                    if t.name not in reads:
                        out["skipped"][t.name] = "write tool (never called)"
                if creds or cfg:
                    # prove the server fails cleanly without them, with one call
                    first = next((n for n in reads if not (vocab[n]["input"].get("required"))), reads[0] if reads else None)
                    if first:
                        args = {k: "x" for k in vocab[first]["input"].get("required", [])}
                        rec = await runner.call(s, first, args, rate)
                        rec.pop("result", None)
                        out["calls"].append(rec)
                        out["checks"]["clean_missing_credentials"] = rec.get("error") == "auth_error" and "PLATFORM_MCP_" in (rec.get("message") or "")
                    out["missing"] = creds + cfg
                    return out
                lists: dict[str, list] = {}
                order = sorted(reads, key=lambda n: (n in DETAIL or n in plan.get("ids", {}), n))
                for verb in order:
                    v = vocab[verb]
                    if verb in plan.get("skip", {}):
                        out["skipped"][verb] = plan["skip"][verb]
                        continue
                    if generic:
                        # tools from the API's own operations: the plan gives the arguments (nothing to guess)
                        args = {k: val for k, val in dict(plan.get("args", {}).get(verb, {})).items() if val is not None}
                        need = [r for r in v["input"].get("required", []) if r not in args]
                        if need:
                            out["skipped"][verb] = f"needs arguments {need}: give them in the plan (args.{verb})"
                            continue
                        rec = await runner.call(s, verb, args, rate)
                        rec["schema_errors"] = [] if rec["is_error"] else schema_errors(v["output"], rec.get("result"))
                        if not rec["is_error"]:
                            data = (rec.get("result") or {}).get("data")
                            rec["count"] = len(data) if isinstance(data, (list, dict, str)) else (0 if data is None else 1)
                            if isinstance(data, list):
                                rec["first_ids"] = [str(x) for x in item_ids(data, "id")[:5]] or None
                        out["calls"].append(rec)
                        continue
                    lk = list_key(v["output"])
                    if verb in DETAIL or verb in plan.get("ids", {}) or verb == "analytics_post":
                        # detail tool: an id from a list result (or the plan), then the same with a bad id
                        srcs, arg, field = DETAIL.get(verb, ((), (v["input"].get("required") or ["id"])[0], "id"))
                        ident = plan.get("ids", {}).get(verb)
                        if isinstance(ident, str) and ident.startswith("hn:"):
                            ident = hn_thread_kid(ident[3:])
                        elif isinstance(ident, str) and ident.startswith("from:"):
                            # from:<list verb>:<path in the first item> (a JSON-encoded list yields its first element)
                            _, src, path = ident.split(":", 2)
                            first = (lists.get(src) or [None])[0]
                            val = first
                            for part in path.split("."):
                                val = val.get(part) if isinstance(val, dict) else None
                            if isinstance(val, str) and val.startswith("["):
                                val = (json.loads(val) or [None])[0]
                            if isinstance(val, list):
                                val = val[0] if val else None
                            ident = str(val) if val not in (None, "") else None
                            if ident is None:
                                out["skipped"][verb] = f"no id available from {src}"
                                continue
                        src_item = None
                        if reuse and verb in reuse.get("ids", {}):
                            ident = reuse["ids"][verb]
                        if ident is None:
                            for src in srcs:
                                for it in lists.get(src, []):
                                    if isinstance(it, dict) and it.get(field) not in (None, ""):
                                        ident, src_item = str(it[field]), it
                                        break
                                if ident:
                                    break
                        if ident is None:
                            out["skipped"][verb] = "no id available (the list tool returned nothing to look up)"
                            continue
                        args = {arg: ident, **plan.get("args", {}).get(verb, {})}
                        if verb == "get_candles":
                            args.setdefault("interval", "1h")
                            args.setdefault("limit", 5)
                        rec = await runner.call(s, verb, args, rate)
                        rec["schema_errors"] = [] if rec["is_error"] else schema_errors(v["output"], rec.get("result"))
                        res = rec.get("result") or {}
                        if not rec["is_error"]:
                            if lk:
                                rec["count"] = len(res.get(lk) or [])
                            if field == "id" and not lk:
                                got = res.get("id") if verb != "analytics_post" else res.get("post_id")
                                rec["same_item"] = str(got) == str(ident) or (src_item is not None and src_item.get("title") and src_item.get("title") == res.get("title"))
                            elif field == "symbol" and not lk:
                                rec["same_item"] = str(res.get("symbol", "")).upper().replace("-", "").replace("/", "") == str(ident).upper().replace("-", "").replace("/", "")
                            elif not lk and field in (v["output"].get("properties") or {}):
                                rec["same_item"] = str(res.get(field, "")).upper() == str(ident).upper()  # e.g. decode_vin echoes the vin
                        out["ids"] = {**out.get("ids", {}), verb: ident}
                        out["calls"].append(rec)
                        bad = {arg: BAD_ID if field == "id" else "ZZZNOTASYMBOL", **{k: val for k, val in args.items() if k != arg}}
                        brec = await runner.call(s, verb, bad, rate)
                        brec["bad_id_probe"] = True
                        brec["clean_error"] = brec["is_error"] and brec.get("error") not in ("client_exception", "internal_error")
                        if not brec["is_error"] and lk and not ((brec.get("result") or {}).get(lk)):
                            brec["clean_error"] = True  # a list-shaped answer (candles, points) may simply be empty
                        brec.pop("result", None) if brec["is_error"] else None
                        out["calls"].append(brec)
                        continue
                    # list or plain read tool
                    args = dict(DEFAULT_ARGS.get(verb, {}))
                    if entry["category"] == "sales" and verb == "search":
                        args = dict(SALES_SEARCH)
                    props = v["input"].get("properties") or {}
                    args = {k: val for k, val in args.items() if k in props}
                    args.update(plan.get("args", {}).get(verb, {}))
                    args = {k: val for k, val in args.items() if val is not None}
                    for req in v["input"].get("required", []):
                        args.setdefault(req, "developer" if req == "query" else "x")
                    rec = await runner.call(s, verb, args, rate)
                    rec["schema_errors"] = [] if rec["is_error"] else schema_errors(v["output"], rec.get("result"))
                    res = rec.get("result") or {}
                    if lk and not rec["is_error"]:
                        items = res.get(lk) or []
                        lists[verb] = items
                        rec["count"] = len(items)
                        rec["first_ids"] = [str(x) for x in item_ids(items, "symbol" if lk in ("results", "markets") else "id")[:5]]
                        rec["next_page"] = res.get("next_page")
                        rec["next_cursor"] = bool(res.get("next_cursor"))
                    out["calls"].append(rec)
                    # page 2
                    if lk and not rec["is_error"] and is_paginated(v["input"]) and rec.get("count"):
                        if plan.get("no_page2"):
                            out["skipped"][f"{verb}:page2"] = plan["no_page2"]
                        elif res.get("next_cursor"):
                            p2 = {**args, "cursor": res["next_cursor"]}
                        elif res.get("next_page"):
                            p2 = {**args, "page": res["next_page"]}
                        else:
                            p2 = None
                            out["skipped"][f"{verb}:page2"] = "result says there is no next page"
                        if not plan.get("no_page2") and p2:
                            rec2 = await runner.call(s, verb, p2, rate)
                            rec2["page2"] = True
                            rec2["schema_errors"] = [] if rec2["is_error"] else schema_errors(v["output"], rec2.get("result"))
                            if not rec2["is_error"]:
                                items2 = (rec2.get("result") or {}).get(lk) or []
                                f = "symbol" if lk in ("results", "markets") else "id"
                                a_ids, b_ids = [str(x) for x in item_ids(items, f)], [str(x) for x in item_ids(items2, f)]
                                rec2["count"] = len(items2)
                                rec2["first_ids"] = b_ids[:5]
                                rec2["advances"] = bool(items2) and a_ids != b_ids and not (set(b_ids) <= set(a_ids))
                            out["calls"].append(rec2)
    except Exception as exc:
        while isinstance(exc, BaseExceptionGroup) and exc.exceptions:
            exc = exc.exceptions[0]
        out["startup_error"] = f"{exc.__class__.__name__}: {exc}"[:400]
    out["wall_ms"] = int((time.monotonic() - t0) * 1000)
    return out


def classify(run: dict) -> tuple[str, str]:
    """Automatic classification; notes name what failed. Root causes are added by a human in the
    catalog's live_check.notes after reading the recorded calls."""
    if run.get("startup_error"):
        return "broken", "server did not start: " + run["startup_error"][:160]
    if run.get("missing"):
        clean = run["checks"].get("clean_missing_credentials")
        return "needs_credentials", f"requires {', '.join(run['missing'])}; " + ("started, listed tools and answered a clean auth_error naming the variables" if clean else "did NOT fail cleanly without them")
    calls = [c for c in run["calls"] if not c.get("bad_id_probe")]
    if not calls:
        return "broken", "no read tool could be called"
    if any(_blocked(c) for c in calls):
        c = next(c for c in calls if _blocked(c))
        return "blocked", f"{c['tool']}: {c.get('http_status') or ''} {c.get('message', '')[:140]}".strip()
    primary = [c for c in calls if not c.get("page2")]
    failed = [c for c in primary if c["is_error"]]
    empty = [c for c in primary if not c["is_error"] and c.get("count") == 0 and c["tool"] not in run.get("may_be_empty", [])]
    schema = [c for c in calls if c.get("schema_errors")]
    problems = []
    for c in failed:
        problems.append(f"{c['tool']} failed: {c.get('error')} {c.get('http_status') or ''} {c.get('message', '')[:120]}".strip())
    for c in empty:
        problems.append(f"{c['tool']} returned no items for {json.dumps(c['args'], ensure_ascii=False)[:80]}")
    for c in schema:
        problems.append(f"{c['tool']} schema: {c['schema_errors'][0]}")
    for c in calls:
        if c.get("page2") and c.get("advances") is False:
            problems.append(f"{c['tool']} page 2 repeats page 1")
        if c.get("page2") and c["is_error"]:
            problems.append(f"{c['tool']} page 2 failed: {c.get('error')} {c.get('message', '')[:100]}")
        if c.get("same_item") is False:
            problems.append(f"{c['tool']} returned a different item than requested")
    for c in run["calls"]:
        if c.get("bad_id_probe") and not c.get("clean_error"):
            problems.append(f"{c['tool']} bad id: " + ("no error (returned a record)" if not c["is_error"] else f"crash {c.get('message', '')[:100]}"))
    list_calls = [c for c in primary if "count" in c and c["tool"] not in DETAIL]
    main_ok = any(not c["is_error"] and (c.get("count") or "count" not in c) and not c.get("schema_errors") for c in (list_calls or primary))
    if not problems:
        return "working", "all read tools answered, schema-valid" + (", pagination advances" if any(c.get("advances") for c in calls) else "")
    if not main_ok:
        return "broken", "; ".join(problems)[:600]
    return "degraded", "; ".join(problems)[:600]


def parity(py: dict, ts: dict, volatile: bool = False) -> dict:
    """Compare the two implementations: tool list and schemas, and per call the error kind, item
    count, first ids and the set of normalised keys (live data can move between the two runs).
    `volatile` (a plan's "volatile": "<why>", for feeds ordered by last modification that change between the
    two runs: Prozorro): differing ids and identity values are drift notes, not parity failures; error kinds,
    keys and value types are still compared."""
    diffs, notes = [], []
    if py.get("tools") != ts.get("tools"):
        diffs.append(f"tools differ: {py.get('tools')} vs {ts.get('tools')}")
    for name in set(py.get("schemas", {})) & set(ts.get("schemas", {})):
        a, b = py["schemas"][name], ts["schemas"][name]
        if a["in"] != b["in"]:
            diffs.append(f"{name}: input schema differs")
        if a["out"] != b["out"]:
            diffs.append(f"{name}: output schema differs")
        if a["read_only"] != b["read_only"]:
            diffs.append(f"{name}: annotations differ")
    for a, b in zip(py.get("calls", []), ts.get("calls", [])):
        if a["tool"] != b["tool"]:
            diffs.append(f"call order differs: {a['tool']} vs {b['tool']}")
            continue
        tag = a["tool"] + (" p2" if a.get("page2") else "") + (" bad-id" if a.get("bad_id_probe") else "")
        if a["is_error"] != b["is_error"] or a.get("error") != b.get("error"):
            diffs.append(f"{tag}: py {a.get('error') or 'ok'} vs ts {b.get('error') or 'ok'}")
            continue
        if a.get("first_ids") != b.get("first_ids") and a.get("first_ids") is not None:
            (notes if volatile else diffs).append(f"{tag}: first ids {a.get('first_ids')[:3]} vs {(b.get('first_ids') or [])[:3]}" + (" (volatile feed)" if volatile else ""))
        ra, rb = a.get("result"), b.get("result")
        if isinstance(ra, dict) and isinstance(rb, dict) and not a["is_error"]:
            ka, kb = _norm_keys(ra), _norm_keys(rb)
            if ka != kb:
                diffs.append(f"{tag}: normalised keys differ {sorted(ka ^ kb)[:6]}")
            va, vb = _first_values(ra), _first_values(rb)
            # identity fields must match exactly; live-moving values (prices, times, counts) must match in type
            bad = [k for k in set(va) | set(vb) if (va.get(k) != vb.get(k)) if k in IDENTITY and not volatile]
            # a volatile feed compares different records: a field present in one and null in the other is not a type difference
            bad += [k for k in set(va) | set(vb) if k not in IDENTITY and _jtype(va.get(k)) != _jtype(vb.get(k))
                    and not (volatile and None in (va.get(k), vb.get(k)))]
            if bad:
                diffs.append(f"{tag}: values differ for {sorted(bad)[:6]}")
            drift = sorted(k for k in set(va) | set(vb) if k not in IDENTITY and va.get(k) != vb.get(k))
            if drift:
                notes.append(f"{tag}: live values moved between the runs for {drift[:6]} (same types)")
    if len(py.get("calls", [])) != len(ts.get("calls", [])):
        diffs.append(f"call counts differ: {len(py.get('calls', []))} vs {len(ts.get('calls', []))}")
    return {"equal": not diffs, "diffs": diffs[:12], "drift": notes[:6]}


IDENTITY = {"id", "symbol", "title", "name", "url", "company", "buyer", "post_id", "listing_id", "series_id"}


def _jtype(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, (int, float)):
        return "number"
    return type(v).__name__


def _first_record(r: dict) -> dict:
    if isinstance(r.get("data"), dict):
        return r["data"]  # a generic tool's answer (generic.py): compare the record itself
    for k, v in r.items():
        if isinstance(v, list) and v and isinstance(v[0], dict) and k != "raw":
            return v[0]
    return r


def _norm_keys(r: dict) -> set:
    rec = _first_record(r)
    return {k for k in rec if k != "raw"} | {f"top:{k}" for k in r if k != "raw"}


def _first_values(r: dict) -> dict:
    rec = _first_record(r)
    return {k: v for k, v in rec.items() if k != "raw" and not isinstance(v, (dict, list))}


def strip_results(run: dict) -> dict:
    """The JSON report keeps the checks, not the payloads (the raw records can be large)."""
    for c in run.get("calls", []):
        c.pop("result", None)
    run.pop("schemas", None)
    return run


async def main_async(args) -> dict:
    only = [x.strip() for x in args.only.split(",")] if args.only else None
    entries = load_entries(args.auth if args.auth != "any" else None, only, args.env, args.entry)
    if args.env != "production" and not entries:
        raise SystemExit(f"no served entry matching the selection declares adapter.environments.{args.env}")
    if args.plan:
        # a plan for one server given on the command line (the forge's live_verify tool): merged over PLANS
        if len(entries) != 1:
            raise SystemExit(f"--plan needs --only naming exactly one served entry (matched {len(entries)})")
        plan = json.loads(Path(args.plan[1:]).read_text(encoding="utf-8")) if args.plan.startswith("@") else json.loads(args.plan)
        if not isinstance(plan, dict) or set(plan) - PLAN_KEYS:
            raise SystemExit(f"--plan must be a JSON object with keys among {sorted(PLAN_KEYS)}")
        key = f"{entries[0]['category']}/{entries[0]['id']}"
        PLANS[key] = {**PLANS.get(key, {}), **plan}
    scratch = Path(args.scratch or os.environ.get("TMPDIR", "/tmp")) / "live_verify"
    scratch.mkdir(parents=True, exist_ok=True)
    runner = Runner(args.delay, args.timeout)
    report = {"generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "egress": args.egress,
              "auth": args.auth, "lang": args.lang, "environment": args.env, "servers": []}
    from . import egress as egress_guard
    for i, e in enumerate(entries, 1):
        key = f"{e['category']}/{e['id']}"
        # the hosts this run would contact (with the plan's config and the selected environment) must be public
        pre = f"PLATFORM_MCP_{e['id'].upper()}_"
        view = {k: v for k, v in os.environ.items() if k.startswith(pre)}
        view.update({pre + str(n).upper(): str(v) for n, v in PLANS.get(key, {}).get("config", {}).items()})
        if args.env != "production":
            view[pre + "ENV"] = args.env
        problems = await egress_guard.blocked(e, view)
        if problems:
            msg = f"{key}: not called: " + "; ".join(problems)
            if len(entries) == 1:
                raise SystemExit(msg)
            print(f"[{i}/{len(entries)}] {msg}", file=sys.stderr, flush=True)
            continue
        py = await verify_server(e, "py", runner, scratch, env_name=args.env) if args.lang in ("py", "both") else None
        ts = await verify_server(e, "ts", runner, scratch, reuse=py, env_name=args.env) if args.lang in ("ts", "both") else None
        primary = py or ts
        status, notes = classify(primary)
        row = {"server": key, "status": status, "notes": notes, "run": primary}
        if py and ts:
            row["ts_status"], row["ts_notes"] = classify(ts)
            row["parity"] = parity(py, ts, volatile=bool(PLANS.get(key, {}).get("volatile")))
            row["ts_run"] = ts
        for r in (py, ts):
            if r:
                strip_results(r)
        report["servers"].append(row)
        print(f"[{i}/{len(entries)}] {key}: {status} — {notes[:160]}" + (f" | parity {'ok' if row['parity']['equal'] else row['parity']['diffs'][:2]}" if row.get("parity") else ""), flush=True)
    counts: dict[str, int] = {}
    for s in report["servers"]:
        counts[s["status"]] = counts.get(s["status"], 0) + 1
    report["summary"] = counts
    return report


def _cell(text: Any) -> str:
    return str(text if text is not None else "").replace("|", "\\|").replace("\n", " ")


def render_markdown(report: dict, compare: dict | None = None, preamble: str = "") -> str:
    """docs/LIVE_VERIFICATION.md: summary, parity, egress comparison and one row per server."""
    rows = report["servers"]
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    out = ["# Live verification", "",
           f"Generated by `platform-mcp-hub verify` on {report['generated_at']} from **{report.get('egress')}**"
           f" (auth type `{report.get('auth')}`, languages `{report.get('lang')}`). Every READ tool was called over stdio exactly as an MCP"
           " client would; write tools were never called. Rerun: `platform-mcp-hub verify --lang both --json report.json`.", ""]
    reruns = sorted({x for r in report.get("reruns", []) for x in (r["servers"] if isinstance(r, dict) else r)})
    if reruns:
        out += [f"{len(reruns)} servers were verified again after their fixes (targeted reruns, same egress, same checks); their rows"
                f" show the rerun: {', '.join(reruns)}.", ""]
    if preamble:
        out += [preamble.rstrip(), ""]
    out += ["## Summary", "", "| status | servers |", "|---|---|"]
    for st in STATUSES:
        out.append(f"| {st} | {counts.get(st, 0)} |")
    out.append(f"| **total** | **{len(rows)}** |")
    par = [r for r in rows if r.get("parity")]
    if par:
        eq = [r for r in par if r["parity"]["equal"]]
        out += ["", "## Python / TypeScript parity", "",
                f"{len(eq)} of {len(par)} servers answered identically in both implementations (same tools and schemas, same error kinds, same"
                " item ids and normalised keys, identity fields equal, every other field of the same JSON type; live values such as prices"
                " may move between the two runs).", ""]
        diff = [r for r in par if not r["parity"]["equal"]]
        if diff:
            out += ["| server | differences |", "|---|---|"] + [f"| {r['server']} | {_cell('; '.join(r['parity']['diffs']))} |" for r in diff]
    if compare:
        cmp = {r["server"]: r for r in compare["servers"]}
        both = [r for r in rows if r["server"] in cmp]
        out += ["", f"## Egress comparison: {report.get('egress')} vs {compare.get('egress')}", "",
                f"| server | {report.get('egress') or 'first'} | {compare.get('egress') or 'second'} | median latency first / second (ms) |", "|---|---|---|---|"]
        for r in both:
            c = cmp[r["server"]]
            out.append(f"| {r['server']} | {r['status']} | {c['status']} | {_median(r['run'])} / {_median(c['run'])} |")
    out += ["", "## Per server", "",
            "Columns: read tools called (write tools skipped), median / max call latency, whether page 2 advanced, whether get(id) returned the"
            " item from the search, whether a bad id gave a clean tool error, Python/TypeScript parity.", "",
            "| server | status | reads called | latency ms (median / max) | page 2 | get(id) | bad id | parity | notes |",
            "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        run = r["run"]
        calls = [c for c in run.get("calls", [])]
        reads = sorted({c["tool"] for c in calls})
        lat = sorted(c.get("latency_ms", 0) for c in calls)
        p2 = [c for c in calls if c.get("page2")]
        page2 = "n/a" if not p2 else ("yes" if all(c.get("advances") for c in p2) else "no")
        same = [c.get("same_item") for c in calls if "same_item" in c]
        get_ok = "n/a" if not same else ("yes" if all(same) else "no")
        bad = [c for c in calls if c.get("bad_id_probe")]
        bad_ok = "n/a" if not bad else ("clean" if all(c.get("clean_error") for c in bad) else "no")
        parity = "n/a" if not r.get("parity") else ("equal" if r["parity"]["equal"] else "differs")
        latency = f"{_median(run)} / {lat[-1]}" if lat else "-"
        out.append(f"| {r['server']} | {r['status']} | {', '.join(reads) or '-'} | {latency} | {page2} | {get_ok} | {bad_ok} | {parity} | {_cell(r.get('final_notes') or r['notes'])} |")
    return "\n".join(out) + "\n"


def _median(run: dict) -> int | str:
    lat = sorted(c.get("latency_ms", 0) for c in run.get("calls", []))
    return lat[len(lat) // 2] if lat else "-"


def record(report: dict, date: str) -> None:
    """Write each server's result into its catalog entry as live_check {date, status, egress, notes}
    (environment_checks.<env>.live_check for a report made with --env)."""
    for row in report["servers"]:
        cat, pid = row["server"].split("/")
        path = SOURCES.get(row["server"]) or (_catalog.catalog_dir() / cat / f"{pid}.json")
        d = json.loads(path.read_text(encoding="utf-8"))
        notes = row.get("final_notes") or row["notes"]
        if row.get("ts_status") and row["ts_status"] != row["status"] and not row.get("final_notes"):
            notes += f"; TypeScript: {row['ts_status']} — {row.get('ts_notes', '')}"
        if row.get("parity") and not row["parity"].get("equal") and not row.get("final_notes"):
            notes += "; Python/TypeScript differ: " + "; ".join(row["parity"].get("diffs", []))[:200]
        block = {"date": date, "status": row["status"], "egress": report.get("egress") or "unknown", "notes": notes}
        env = report.get("environment") or "production"
        if env == "production":
            d["live_check"] = block
        else:  # a vendor environment's result never replaces the production live_check
            d.setdefault("environment_checks", {}).setdefault(env, {})["live_check"] = block
        path.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="platform-mcp-hub verify", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="comma-separated ids or category/id")
    ap.add_argument("--entry", action="append", help="verify this entry file instead of the catalog (repeatable; --record writes into it)")
    ap.add_argument("--auth", default="none", help="adapter auth type to select (default none; 'any' for all)")
    ap.add_argument("--lang", default="py", choices=["py", "ts", "both"])
    ap.add_argument("--egress", default=None, help="label for where the calls leave from (e.g. 'datacenter' or 'residential'); never an address")
    ap.add_argument("--json", help="write the JSON report here")
    ap.add_argument("--delay", type=float, default=1.0, help="minimum seconds between calls (default 1)")
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--scratch", help="scratch directory for the TypeScript launcher")
    ap.add_argument("--record", action="store_true", help="write live_check into each catalog entry")
    ap.add_argument("--env", default="production", help="vendor environment to verify (adapter.environments name, e.g. sandbox); default production")
    ap.add_argument("--plan", help="with --only <one entry>: a JSON plan (or @file) merged over PLANS: {config, args, ids, skip, no_page2, may_be_empty}")
    ap.add_argument("--from-json", help="do not call anything: load this earlier JSON report (e.g. to --record it)")
    ap.add_argument("--merge", action="append", default=[], help="with --from-json: a later report whose servers replace the same servers (a targeted rerun after a fix)")
    ap.add_argument("--markdown", help="write a Markdown report (docs/LIVE_VERIFICATION.md) from the report")
    ap.add_argument("--compare", help="a second JSON report from another egress (e.g. residential) for the egress comparison table")
    ap.add_argument("--preamble", help="a Markdown file inserted under the heading (fixes made, root causes)")
    args = ap.parse_args(argv)
    report = json.loads(Path(args.from_json).read_text(encoding="utf-8")) if args.from_json else asyncio.run(main_async(args))
    for extra in args.merge:
        later = {r["server"]: r for r in json.loads(Path(extra).read_text(encoding="utf-8"))["servers"]}
        report["servers"] = [later.get(r["server"], r) for r in report["servers"]]
        report.setdefault("reruns", []).append({"servers": sorted(later), "from": extra})
    if args.merge or args.from_json:
        report["summary"] = {}
        for r in report["servers"]:
            report["summary"][r["status"]] = report["summary"].get(r["status"], 0) + 1
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    if args.record:
        record(report, report["generated_at"][:10])
    if args.markdown:
        compare = json.loads(Path(args.compare).read_text(encoding="utf-8")) if args.compare else None
        pre = Path(args.preamble).read_text(encoding="utf-8") if args.preamble else ""
        Path(args.markdown).write_text(render_markdown(report, compare, pre), encoding="utf-8")
    print("summary:", report.get("summary"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
