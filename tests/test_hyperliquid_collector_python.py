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

SPEC = json.loads((ROOT / "catalog" / "market_data" / "hyperliquid_collector.json").read_text(encoding="utf-8"))


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_candles_stay_not_offered_until_the_runtime_can_cast_timestamps():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["me", "search_symbols"]
    assert set(SPEC["adapter"]["not_offered"]) == {"get_candles", "get_series", "get_news"}
    assert "startTime" in SPEC["adapter"]["not_offered"]["get_candles"]


@pytest.mark.asyncio
@respx.mock
async def test_search_symbols_posts_meta_and_maps_the_universe():
    route = respx.post("https://api.hyperliquid.xyz/info").mock(return_value=httpx.Response(200, json={
        "universe": [{"name": "BTC", "szDecimals": 5, "maxLeverage": 40}, {"name": "ETH", "szDecimals": 4, "maxLeverage": 25, "isDelisted": False}], "marginTables": []}))
    res = await _server().call_tool("search_symbols", {"query": "BTC"})
    assert res.is_error is False
    rs = res.structured_content["results"]
    assert rs[0] == {"symbol": "BTC", "type": "perpetual", "raw": {"name": "BTC", "szDecimals": 5, "maxLeverage": 40}} and rs[1]["symbol"] == "ETH"
    assert json.loads(route.calls.last.request.content) == {"type": "meta"}
    assert res.structured_content["next_page"] is None


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_is_error_result():
    respx.post("https://api.hyperliquid.xyz/info").mock(return_value=httpx.Response(429, text="Too many requests"))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited"
