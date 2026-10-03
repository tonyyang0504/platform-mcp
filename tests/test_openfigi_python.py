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

SPEC = json.loads((ROOT / "catalog" / "market_data" / "openfigi.json").read_text(encoding="utf-8"))
URL = "https://api.openfigi.com/v3/search"
PAGE = {"data": [{"figi": "BBG000BLNNH6", "name": "INTL BUSINESS MACHINES CORP", "ticker": "IBM", "exchCode": "US", "compositeFIGI": "BBG000BLNNH6",
                  "securityType": "Common Stock", "marketSector": "Equity", "shareClassFIGI": "BBG001S5S399", "securityType2": "Common Stock", "securityDescription": "IBM"}],
        "next": "QW9JSVFiUjVnQ3hDUWtjd01EUldNVmhPT1RnPSAx.U3RLauajVvoJIHY1X6ZsAY7rASWavQxDedwFiL8neJQ="}


def _server(creds=None):
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], creds or {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
async def test_one_read_tool_and_the_documented_rate():
    tools = await _server().list_tools()
    assert [t.name for t in tools] == ["search_symbols"]
    assert SPEC["adapter"]["rate_per_second"] <= 5 / 60 + 1e-9  # 5 searches per minute without a key


@pytest.mark.asyncio
@respx.mock
async def test_search_posts_the_query_and_returns_the_next_cursor():
    route = respx.post(URL).mock(return_value=httpx.Response(200, json=PAGE))
    res = await _server().call_tool("search_symbols", {"query": "ibm"})
    assert res.is_error is False
    s = res.structured_content
    assert s["results"][0]["symbol"] == "BBG000BLNNH6" and s["results"][0]["name"] == "INTL BUSINESS MACHINES CORP" and s["results"][0]["type"] == "Common Stock"
    assert s["next_cursor"] == PAGE["next"]
    assert s["next_page"] is None  # cursor-only: `page` is ignored by the tool, so no next_page is offered
    req = route.calls.last.request
    assert json.loads(req.content) == {"query": "ibm"} and "X-OPENFIGI-APIKEY" not in req.headers


@pytest.mark.asyncio
@respx.mock
async def test_cursor_goes_back_as_start_and_the_optional_key_as_header():
    route = respx.post(URL).mock(return_value=httpx.Response(200, json={"data": []}))
    res = await _server({"api_key": "k-123456789"}).call_tool("search_symbols", {"query": "ibm", "cursor": PAGE["next"]})
    assert res.is_error is False and res.structured_content["next_cursor"] is None
    req = route.calls.last.request
    assert json.loads(req.content) == {"query": "ibm", "start": PAGE["next"]} and req.headers["X-OPENFIGI-APIKEY"] == "k-123456789"


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_a_tool_error():
    respx.post(URL).mock(return_value=httpx.Response(429, headers={"Retry-After": "60"}, text="Too Many Requests."))
    res = await _server().call_tool("search_symbols", {"query": "ibm"})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited"


HUNDRED = {"data": [{"figi": f"BBG{i:09d}", "name": f"N{i}", "securityType": "Common Stock"} for i in range(100)], "next": "CUR1"}


@pytest.mark.asyncio
@respx.mock
async def test_fixed_100_row_pages_are_trimmed_to_limit_with_cursors_that_walk_the_rest():
    # the API ignores the page size (always 100): the tool returns `limit` rows and a cursor into the rest of the page
    route = respx.post(URL).mock(side_effect=[httpx.Response(200, json=HUNDRED), httpx.Response(200, json={"data": [{"figi": "BBGNEXT", "name": "x"}]})])
    s = _server()
    p1 = (await s.call_tool("search_symbols", {"query": "ibm", "limit": 40})).structured_content
    assert [r["symbol"] for r in p1["results"]] == [f"BBG{i:09d}" for i in range(40)]
    assert p1["next_cursor"] == "pmc1.W251bGwsNDBd" and p1["next_page"] is None  # [null, 40]: the same bytes in both runtimes
    p2 = (await s.call_tool("search_symbols", {"query": "ibm", "limit": 40, "cursor": p1["next_cursor"]})).structured_content
    assert [r["symbol"] for r in p2["results"]] == [f"BBG{i:09d}" for i in range(40, 80)] and p2["next_cursor"] == "pmc1.W251bGwsODBd"
    p3 = (await s.call_tool("search_symbols", {"query": "ibm", "limit": 40, "cursor": p2["next_cursor"]})).structured_content
    assert [r["symbol"] for r in p3["results"]] == [f"BBG{i:09d}" for i in range(80, 100)]
    assert p3["next_cursor"] == "CUR1"  # end of this upstream page: the platform's own cursor
    assert route.call_count == 1  # the three windows came from one search (5 per minute without a key)
    p4 = (await s.call_tool("search_symbols", {"query": "ibm", "limit": 40, "cursor": "CUR1"})).structured_content
    assert [r["symbol"] for r in p4["results"]] == ["BBGNEXT"] and p4["next_cursor"] is None
    assert json.loads(route.calls.last.request.content) == {"query": "ibm", "start": "CUR1"}


@pytest.mark.asyncio
@respx.mock
async def test_a_window_cursor_inside_a_later_page_resends_that_page_cursor_and_a_forged_cursor_is_invalid():
    import base64
    route = respx.post(URL).mock(return_value=httpx.Response(200, json=HUNDRED))
    cur = "pmc1." + base64.urlsafe_b64encode(json.dumps(["CUR0", 90], separators=(",", ":")).encode()).decode().rstrip("=")
    res = (await _server().call_tool("search_symbols", {"query": "ibm", "limit": 25, "cursor": cur})).structured_content
    assert json.loads(route.calls.last.request.content) == {"query": "ibm", "start": "CUR0"}
    assert [r["symbol"] for r in res["results"]] == [f"BBG{i:09d}" for i in range(90, 100)] and res["next_cursor"] == "CUR1"
    bad = await _server().call_tool("search_symbols", {"query": "ibm", "cursor": "pmc1.!!notbase64"})
    assert bad.is_error is True and bad.structured_content["error"] == "invalid_input"
