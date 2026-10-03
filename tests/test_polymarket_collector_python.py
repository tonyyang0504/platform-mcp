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

SPEC = json.loads((ROOT / "catalog" / "market_data" / "polymarket_collector.json").read_text(encoding="utf-8"))

# https://gamma-api.polymarket.com/markets?limit=1&closed=false (opened 2026-09-24)
MARKET = {
    "id": "559651", "question": "Xi Jinping out before 2027?", "conditionId": "0xa467b14d51f01b957109d9cbb1d6c124fab2a089d52ed8f471d23c2812e743b7", "slug": "xi-jinping-out-before-2027",
    "endDate": "2027-01-01T04:59:00Z", "liquidity": "511522.38527", "startDate": "2025-01-10T00:00:00Z", "description": "...", "outcomes": "[\"Yes\", \"No\"]", "outcomePrices": "[\"0.0425\", \"0.9575\"]",
    "volume": "13900795.795055997", "active": True, "closed": False, "marketType": "normal", "clobTokenIds": "[\"1234\", \"5678\"]",
}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_market_data_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_series", "me", "search_symbols"]
    assert all(t.annotations.read_only_hint is True for t in tools)
    gs = next(t for t in tools if t.name == "get_series")
    assert gs.meta["platform_mcp/endpoint"] == "https://data-api.polymarket.com/v2/prices-history"


@pytest.mark.asyncio
@respx.mock
async def test_search_symbols_lists_gamma_markets_with_offset_paging():
    respx.get("https://gamma-api.polymarket.com/markets").mock(return_value=httpx.Response(200, json=[MARKET]))
    res = await _server().call_tool("search_symbols", {"query": "xi", "limit": 20, "page": 3})
    assert res.is_error is False
    r = res.structured_content["results"][0]
    assert r["symbol"] == "xi-jinping-out-before-2027" and r["name"] == "Xi Jinping out before 2027?" and r["type"] == "normal" and r["raw"]["conditionId"].startswith("0xa467")
    q = respx.calls.last.request.url.params
    assert q["limit"] == "20" and q["offset"] == "40" and "q" not in q and "query" not in q


@pytest.mark.asyncio
@respx.mock
async def test_get_series_reads_price_history_from_the_data_api():
    # docs.polymarket.com/market-data/prices-order-books example shape
    respx.get("https://data-api.polymarket.com/v2/prices-history").mock(return_value=httpx.Response(200, json={
        "data": [{"timestamp": 1788354000, "price": 0.255, "resolution_seconds": 3600}, {"timestamp": 1788357600, "price": 0.26, "resolution_seconds": 3600}],
        "pagination": {"limit": 2, "has_more": True, "next_cursor": "eyJkYXRhIjp7InR5cGUiOiJwcmljZXNfaGlzdG9yeSJ9fQ=="}}))
    res = await _server().call_tool("get_series", {"series_id": "1234", "start": "1788350000", "end": "1788360000"})
    assert res.is_error is False
    pts = res.structured_content["points"]
    assert pts[0]["time"] == "1788354000" and pts[0]["value"] == 0.255 and len(pts) == 2
    q = respx.calls.last.request.url.params
    assert q["token_id"] == "1234" and q["start"] == "1788350000" and q["end"] == "1788360000"


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_is_error_result():
    respx.get("https://gamma-api.polymarket.com/markets").mock(return_value=httpx.Response(429, headers={"Retry-After": "2"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 2
