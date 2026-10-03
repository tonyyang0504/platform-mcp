"""Regression tests for the fixes found by platform-mcp-hub verify (live check 2026-09-26). Each test
replays a response recorded from the live platform (tests/fixtures/live, personal data scrubbed)
through the catalog entry and validates the result against the vocabulary's output schema, the
same check a strict MCP client (the Python SDK) applies to structuredContent."""
import json
import sys
from pathlib import Path

import httpx
import pytest
import respx
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.adapter import paginates  # noqa: E402
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "live"
VOCAB = json.loads((ROOT / "catalog" / "schema" / "vocab.json").read_text(encoding="utf-8"))


def spec(key: str) -> dict:
    return json.loads((ROOT / "catalog" / f"{key}.json").read_text(encoding="utf-8"))


def server(s: dict, creds: dict | None = None):
    t = Transport(s["adapter"]["base_url"], s["adapter"]["auth"], creds or {}, 50, "test", envelope=s["adapter"].get("envelope"))
    t.fixed_headers = s["adapter"].get("headers") or {}
    return build_server(s, transport=t)


def valid(s: dict, verb: str, payload: dict) -> None:
    errors = [e.message for e in Draft202012Validator(VOCAB[s["category"]][verb]["output"]).iter_errors(payload)]
    assert not errors, errors


def fixture(name: str):
    text = (FIX / name).read_text(encoding="utf-8")
    return json.loads(text) if name.endswith(".json") else text


# --- runtime: a tool that sends no page/offset/cursor never advertises a next page -------------

def test_paginates_detects_page_offset_and_cursor_expressions():
    assert paginates({"path": "/x", "params": {"page": "page"}})
    assert paginates({"path": "/x", "params": {"os": "offset"}})
    assert paginates({"path": "/x", "params": {"p": "page0"}})
    assert paginates({"path": "/x", "params": {"c": "cursor"}})
    assert paginates({"path": "/x", "body": {"from": "str:offset"}})
    assert paginates({"path": "/x/{page}"})
    assert not paginates({"path": "/feed", "params": {"search": "query", "limit": "limit"}})
    assert not paginates({"path": "/feed", "params": {"pagesize": "limit", "x": "@page_token"}})


@pytest.mark.asyncio
@respx.mock
async def test_a_feed_without_paging_answers_next_page_null():
    # live: remote_ok returned 99 postings for limit 10 and next_page 2, and page 2 repeated page 1
    s = spec("jobs/remote_ok")
    rows = [{"legal": "notice"}] + [{"id": str(i), "position": f"Job {i}", "company": "Acme", "slug": f"job-{i}"} for i in range(30)]
    respx.get(url__startswith=s["adapter"]["base_url"]).mock(return_value=httpx.Response(200, json=rows))
    res = await server(s).call_tool("search", {"query": "developer", "limit": 10})
    assert res.is_error is False and len(res.structured_content["postings"]) >= 10
    assert res.structured_content["next_page"] is None


@pytest.mark.asyncio
@respx.mock
async def test_a_paging_tool_still_advertises_the_next_page():
    s = spec("sales/no_brreg")
    respx.get(url__startswith="https://data.brreg.no/enhetsregisteret/api/enheter").mock(return_value=httpx.Response(200, json=fixture("no_brreg_search.json")))
    res = await server(s).call_tool("search", {"query": "equinor", "limit": 2})
    assert res.structured_content["next_page"] == 2 and res.structured_content["total"] == 240


# --- sales/no_brreg: antallAnsatte is an integer, the vocabulary's size a string --------------

@pytest.mark.asyncio
@respx.mock
async def test_no_brreg_size_is_a_string_and_the_result_is_schema_valid():
    s = spec("sales/no_brreg")
    respx.get(url__startswith="https://data.brreg.no/enhetsregisteret/api/enheter").mock(return_value=httpx.Response(200, json=fixture("no_brreg_search.json")))
    res = await server(s).call_tool("search", {"query": "equinor", "limit": 2})
    assert res.is_error is False
    c = res.structured_content["companies"]
    assert c[0]["id"] == "923609016" and c[0]["size"] == "21272" and c[1]["size"] is None
    valid(s, "search", res.structured_content)


# --- deals/world_bank_procurement: some notices have no bid_description ------------------------

@pytest.mark.asyncio
@respx.mock
async def test_world_bank_title_falls_back_to_the_project_name():
    s = spec("deals/world_bank_procurement")
    data = fixture("world_bank_search.json")
    respx.get(url__startswith="https://search.worldbank.org/api/v2/procnotices").mock(return_value=httpx.Response(200, json=data))
    res = await server(s).call_tool("search_postings", {"query": "consulting", "limit": 3})
    assert res.is_error is False
    p = {x["id"]: x for x in res.structured_content["postings"]}
    bare = next(r for r in data["procnotices"] if not r.get("bid_description"))
    assert p[bare["id"]]["title"] == bare["project_name"]
    valid(s, "search_postings", res.structured_content)


# --- deals/contracts_finder: Record/{ocid} answers 404 for every ocid; Release/{id} works --------

@pytest.mark.asyncio
@respx.mock
async def test_contracts_finder_search_ids_feed_get_posting_through_the_release_endpoint():
    s = spec("deals/contracts_finder")
    base = "https://www.contractsfinder.service.gov.uk"
    search = fixture("contracts_finder_search.json")
    release = fixture("contracts_finder_release.json")
    respx.get(f"{base}/Published/Notices/OCDS/Search").mock(return_value=httpx.Response(200, json=search))
    rid = release["releases"][0]["id"]
    route = respx.get(f"{base}/Published/OCDS/Release/{rid}").mock(return_value=httpx.Response(200, json=release))
    srv = server(s)
    res = await srv.call_tool("search_postings", {"limit": 2})
    assert res.is_error is False
    first = res.structured_content["postings"][0]
    assert first["id"] == rid and first["raw"]["ocid"].startswith("ocds-b5fd17-")
    assert res.structured_content["next_page"] is None  # paging is by cursor (links.next), which page cannot carry
    valid(s, "search_postings", res.structured_content)
    got = await srv.call_tool("get_posting", {"id": first["id"]})
    assert got.is_error is False and route.called
    assert got.structured_content["id"] == rid and got.structured_content["title"] == first["title"]
    assert got.structured_content["buyer"] == first["buyer"]
    valid(s, "get_posting", got.structured_content)


# --- jobs/nhs_jobs: 406 Not Acceptable to Accept: application/json -----------------------------

@pytest.mark.asyncio
@respx.mock
async def test_nhs_jobs_asks_for_xml_and_parses_the_recorded_feed():
    s = spec("jobs/nhs_jobs")
    route = respx.get(url__startswith="https://www.jobs.nhs.uk/api/v1/search_xml").mock(
        side_effect=lambda req: httpx.Response(200, headers={"content-type": "application/xml"}, text=fixture("nhs_jobs_search.xml"))
        if req.headers.get("accept") == "application/xml" else httpx.Response(406, json={"status": 406, "error": "Not Acceptable"}))
    res = await server(s).call_tool("search", {"query": "nurse", "limit": 2})
    assert res.is_error is False, res.structured_content
    assert route.calls.last.request.headers["accept"] == "application/xml"
    posts = res.structured_content["postings"]
    assert len(posts) == 2 and posts[0]["id"] and posts[0]["title"]
    valid(s, "search", res.structured_content)


# --- deals/problogger_jobs: /jobs/feed/ is empty; the WPJobBoard feed carries the postings -------

@pytest.mark.asyncio
@respx.mock
async def test_problogger_deals_reads_the_live_board_feed():
    s = spec("deals/problogger_jobs")
    route = respx.get(url__startswith="https://problogger.com/jobs/wpjobboard/xml/rss/").mock(
        return_value=httpx.Response(200, headers={"content-type": "application/rss+xml"}, text=fixture("problogger_wpjobboard_rss.xml")))
    res = await server(s).call_tool("search_postings", {"query": "writer"})
    assert res.is_error is False
    assert len(res.structured_content["postings"]) >= 1 and res.structured_content["next_page"] is None
    assert dict(route.calls.last.request.url.params) == {"query": "writer", "filter": "active"}
    valid(s, "search_postings", res.structured_content)


# --- candles: decimal strings and integer times failed the vocabulary's number/string types ------

@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("key,fixture_name,interval", [
    ("market_data/binance_collector", "binance_klines.json", "1h"),
    ("market_data/binance_vision_collector", "binance_klines.json", "1h"),
    ("market_data/bybit_collector", "bybit_kline.json", "60"),
])
async def test_recorded_candles_are_schema_valid(key, fixture_name, interval):
    s = spec(key)
    raw = fixture(fixture_name)
    respx.get(url__startswith=s["adapter"]["base_url"]).mock(return_value=httpx.Response(200, json=raw))
    res = await server(s).call_tool("get_candles", {"symbol": "BTCUSDT", "interval": interval, "limit": 2})
    assert res.is_error is False, res.structured_content
    c = res.structured_content["candles"][0]
    row = raw[0] if isinstance(raw, list) else raw["result"]["list"][0]
    assert c["time"] == str(row[0]) and c["close"] == float(row[4]) and isinstance(c["open"], (int, float))
    valid(s, "get_candles", res.structured_content)


# --- trading/hyperliquid(_spot): l2Book prices are decimal strings -------------------------------

@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("key", ["trading/hyperliquid", "trading/hyperliquid_spot"])
async def test_hyperliquid_ticker_prices_are_numbers(key):
    s = spec(key)
    book = fixture("hyperliquid_l2book.json")
    respx.post("https://api.hyperliquid.xyz/info").mock(return_value=httpx.Response(200, json=book))
    res = await server(s, {"wallet_address": "0x0000000000000000000000000000000000000000"}).call_tool("get_ticker", {"symbol": "BTC"})
    assert res.is_error is False
    assert res.structured_content["bid"] == float(book["levels"][0][0]["px"]) and res.structured_content["ask"] == float(book["levels"][1][0]["px"])
    valid(s, "get_ticker", res.structured_content)


# --- lint: the live_check block written by platform-mcp-hub verify --record --------------------------

def test_lint_accepts_a_well_formed_live_check_and_rejects_a_bad_one(tmp_path):
    sys.path.insert(0, str(ROOT / "tools"))
    from platform_mcp_hub import lint as lint_catalog

    entry = spec("jobs/remote_ok")
    entry["live_check"] = {"date": "2026-09-26", "status": "working", "egress": "datacenter", "notes": "ok"}
    good = tmp_path / "remote_ok.json"
    good.write_text(json.dumps(entry), encoding="utf-8")
    assert not [e for e in lint_catalog.lint(good)[0] if "live_check" in e]
    entry["live_check"] = {"date": "26/09/2026", "status": "fine", "egress": "", "notes": 1, "extra": True}
    good.write_text(json.dumps(entry), encoding="utf-8")
    assert [e for e in lint_catalog.lint(good)[0] if "live_check" in e]


# --- market_data/bybit_collector: a 200 with retCode != 0 was an empty candle list ----------------

@pytest.mark.asyncio
@respx.mock
async def test_bybit_collector_invalid_symbol_is_an_error_not_an_empty_list():
    s = spec("market_data/bybit_collector")
    respx.get(url__startswith=s["adapter"]["base_url"]).mock(return_value=httpx.Response(200, json=fixture("bybit_kline_invalid_symbol.json")))
    res = await server(s).call_tool("get_candles", {"symbol": "ZZZNOTASYMBOL", "interval": "60"})
    assert res.is_error is True and "Symbol Is Invalid" in res.structured_content["message"]


# --- market_data/polymarket_collector: prices-history timestamps are numbers, time a string -------

@pytest.mark.asyncio
@respx.mock
async def test_polymarket_series_points_are_schema_valid():
    s = spec("market_data/polymarket_collector")
    data = fixture("polymarket_prices_history.json")
    respx.get(url__startswith="https://data-api.polymarket.com/v2/prices-history").mock(return_value=httpx.Response(200, json=data))
    res = await server(s).call_tool("get_series", {"series_id": "123", "start": "1790177880", "end": "1790188680"})
    assert res.is_error is False
    p = res.structured_content["points"][0]
    assert p["time"] == str(data["data"][0]["timestamp"]) and p["value"] == data["data"][0]["price"]
    valid(s, "get_series", res.structured_content)


# --- deals/e_zamowienia: a WAF answers 403 'Access Blocked' to calls ~1-2 s apart -----------------

@pytest.mark.asyncio
@respx.mock
async def test_e_zamowienia_is_paced_to_one_call_per_five_seconds_and_a_waf_block_is_clean():
    s = spec("deals/e_zamowienia")
    assert s["adapter"]["rate_per_second"] <= 0.2
    respx.get(url__startswith=s["adapter"]["base_url"]).mock(return_value=httpx.Response(
        403, headers={"content-type": "text/html"}, text="<!DOCTYPE html><html lang=\"pl\"><head><title>Dostęp zablokowany / Access Blocked</title></head></html>"))
    res = await server(s).call_tool("get_posting", {"id": "2026/BZP 00430547/01"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 403


# --- XML parity: both runtimes parse recorded feeds to the same object ------------------------------
# (live check 2026-09-26: TypeScript kept a CDATA title's trailing space and left &#038; undecoded)

@pytest.mark.parametrize("name", ["coroflot_rss", "jobwebghana_rss", "nhs_jobs_search", "problogger_wpjobboard_rss"])
def test_recorded_feeds_parse_to_the_pinned_object(name):
    from platform_mcp_hub.http import xml_to_obj
    assert xml_to_obj(fixture(f"{name}.xml")) == fixture(f"{name}.parsed.json")


@pytest.mark.asyncio
@respx.mock
async def test_coroflot_cdata_title_is_trimmed_and_jobwebghana_entities_decode():
    s = spec("jobs/coroflot")
    respx.get(url__startswith=s["adapter"]["base_url"]).mock(return_value=httpx.Response(200, headers={"content-type": "application/rss+xml"}, text=fixture("coroflot_rss.xml")))
    res = await server(s).call_tool("search", {"query": "designer"})
    assert res.structured_content["postings"][0]["title"] == "The Wild Collective is seeking a Graphic Designer Licensed Entertainment/Lifestyle"
    parsed = fixture("jobwebghana_rss.parsed.json")
    assert parsed["rss"]["channel"]["item"][0]["guid"]["#text"] == "https://jobwebghana.com/?post_type=job_listing&p=24170"


# --- jobs/eluta: past '2 times per hour' the feed answers 200 with a 'Too Many Requests' item ------

@pytest.mark.asyncio
@respx.mock
async def test_eluta_rate_limit_notice_is_a_rate_limited_error_not_a_posting():
    s = spec("jobs/eluta")
    assert s["adapter"]["rate_per_second"] <= 0.01
    respx.get(url__startswith="https://www.eluta.ca/rss").mock(return_value=httpx.Response(
        200, headers={"content-type": "text/xml; charset=UTF-8"}, text=fixture("eluta_too_many_requests.xml")))
    res = await server(s).call_tool("search", {"query": "developer"})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited"
