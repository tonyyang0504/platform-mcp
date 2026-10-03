import json
import sys
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "market_data" / "frankfurter.json").read_text(encoding="utf-8"))
BASE = "https://api.frankfurter.dev/v2"


def _server(creds=None):
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], creds or {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
async def test_tools_are_the_keyless_reads():
    tools = {t.name: t for t in await _server().list_tools()}
    assert sorted(tools) == ["get_series", "search_symbols"]
    assert all(t.annotations.read_only_hint for t in tools.values())
    assert set(SPEC["adapter"]["not_offered"]) == {"me", "get_candles", "get_news"}


CURRENCIES = [
    {"iso_code": "AUD", "iso_numeric": "036", "name": "Australian Dollar", "symbol": "$", "start_date": "1999-01-04", "end_date": "2026-09-27"},
    {"iso_code": "EUR", "iso_numeric": "978", "name": "Euro", "symbol": "\u20ac", "start_date": "1999-01-04", "end_date": "2026-09-27"},
    {"iso_code": "JPY", "iso_numeric": "392", "name": "Japanese Yen", "symbol": "\u00a5", "start_date": "1999-01-04", "end_date": "2026-09-27"},
    {"iso_code": "USD", "iso_numeric": "840", "name": "United States Dollar", "symbol": "$", "start_date": "1948-06-21", "end_date": "2026-09-27"},
]


@pytest.mark.asyncio
@respx.mock
async def test_search_symbols_filters_the_currency_list_by_code_or_name_and_pages_locally():
    route = respx.get(f"{BASE}/currencies").mock(return_value=httpx.Response(200, json=CURRENCIES))
    s = _server()
    res = await s.call_tool("search_symbols", {"query": "dollar"})
    assert res.is_error is False
    r = res.structured_content
    assert [(x["symbol"], x["name"], x["type"]) for x in r["results"]] == [("AUD", "Australian Dollar", "currency"), ("USD", "United States Dollar", "currency")]
    assert r["total"] == 2 and r["next_page"] is None
    res = await s.call_tool("search_symbols", {"query": "usd", "limit": 1})
    assert [x["symbol"] for x in res.structured_content["results"]] == ["USD"]  # the code, case-insensitive
    p1 = (await s.call_tool("search_symbols", {"query": "a", "limit": 2})).structured_content  # AUD, JPY(Japanese), USD(States)
    p2 = (await s.call_tool("search_symbols", {"query": "a", "limit": 2, "page": 2})).structured_content
    assert [x["symbol"] for x in p1["results"]] == ["AUD", "JPY"] and p1["next_page"] == 2 and p1["total"] == 3
    assert [x["symbol"] for x in p2["results"]] == ["USD"] and p2["next_page"] is None
    assert route.call_count == 1  # the list is fetched once and paged from the short-lived cache
    res = await s.call_tool("search_symbols", {"query": "zzz"})
    assert res.is_error is False and res.structured_content["results"] == [] and res.structured_content["total"] == 0


@pytest.mark.asyncio
@respx.mock
async def test_get_series_maps_rates_and_sends_the_date_range():
    route = respx.get(f"{BASE}/rates").mock(return_value=httpx.Response(200, json=[
        {"date": "2026-09-01", "base": "EUR", "quote": "USD", "rate": 1.1599}, {"date": "2026-09-02", "base": "EUR", "quote": "USD", "rate": 1.1587}]))
    res = await _server({"base_currency": "GBP"}).call_tool("get_series", {"series_id": "USD", "start": "2026-09-01", "end": "2026-09-02"})
    assert res.is_error is False
    assert [(p["time"], p["value"]) for p in res.structured_content["points"]] == [("2026-09-01", 1.1599), ("2026-09-02", 1.1587)]
    q = route.calls.last.request.url.params
    assert (q["quotes"], q["from"], q["to"], q["base"]) == ("USD", "2026-09-01", "2026-09-02", "GBP")


@pytest.mark.asyncio
@respx.mock
async def test_bad_dates_and_bad_codes_are_tool_errors():
    res = await _server().call_tool("get_series", {"series_id": "USD", "start": "01/09/2026"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input"
    respx.get(f"{BASE}/rates").mock(return_value=httpx.Response(422, json={"status": 422, "message": "invalid currency: XXXQ"}))
    res = await _server().call_tool("get_series", {"series_id": "XXXQ"})  # the live answer to an unknown quote currency
    assert res.is_error is True and res.structured_content["error"] == "invalid_input" and res.structured_content["http_status"] == 422
    assert "invalid currency: XXXQ" in res.structured_content["message"]
