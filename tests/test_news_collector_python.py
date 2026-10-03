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

SPEC = json.loads((ROOT / "catalog" / "market_data" / "news_collector.json").read_text(encoding="utf-8"))
API = "https://api.gdeltproject.org/api/v2/doc/doc"
ART = {"url": "https://www.coinspeaker.com/xrp-price/", "url_mobile": "", "title": "AI Predicts XRP Price Action", "seendate": "20260925T021500Z",
       "socialimage": "", "domain": "coinspeaker.com", "language": "English", "sourcecountry": "United States"}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_get_news_is_offered():
    tools = await _server().list_tools()
    assert [t.name for t in tools] == ["get_news"]
    assert set(SPEC["adapter"]["not_offered"]) == {"me", "get_candles", "get_series", "search_symbols"}


@pytest.mark.asyncio
@respx.mock
async def test_get_news_calls_gdelt_artlist_json():
    route = respx.get(url__startswith=API).mock(return_value=httpx.Response(200, headers={"content-type": "application/json"}, json={"articles": [ART]}))
    res = await _server().call_tool("get_news", {"query": "bitcoin", "since": "2026-09-20", "limit": 500})
    assert res.is_error is False, res.structured_content
    a = res.structured_content["articles"][0]
    assert a["id"] == ART["url"] and a["title"] == ART["title"] and a["url"] == ART["url"]
    assert a["published_at"] == "20260925T021500Z" and a["source"] == "coinspeaker.com" and a["raw"]["language"] == "English"
    q = route.calls.last.request.url.params
    assert q["query"] == "bitcoin" and q["mode"] == "artlist" and q["format"] == "json" and q["sort"] == "datedesc"
    assert q["maxrecords"] == "100" and q["startdatetime"] == "20260920000000"


@pytest.mark.asyncio
@respx.mock
async def test_throttle_notice_yields_no_articles_and_errors_surface():
    respx.get(url__startswith=API).mock(side_effect=[
        httpx.Response(200, headers={"content-type": "text/html"}, text="Please limit requests to one every 5 seconds or contact ..."),
        httpx.Response(429, headers={"Retry-After": "5"})])
    res = await _server().call_tool("get_news", {"query": "oil"})
    # a throttle notice served as a 200 HTML page is a rate_limited error, never an empty success (forge stress test 2026-10)
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and "limit requests" in res.structured_content["message"]
    res = await _server().call_tool("get_news", {"query": "oil"})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited"
