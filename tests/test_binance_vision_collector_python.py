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

SPEC = json.loads((ROOT / "catalog" / "market_data" / "binance_vision_collector.json").read_text(encoding="utf-8"))
BASE = "https://data-api.binance.vision"

# developers.binance.com market-data-endpoints: kline rows are positional arrays
KLINE = [1499040000000, "0.01634790", "0.80000000", "0.01575800", "0.01577100", "148976.11427815", 1499644799999, "2434.19055334", 308, "1756.87402397", "28.46694368", "0"]


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_market_data_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_candles", "me", "search_symbols"]
    gc = next(t for t in tools if t.name == "get_candles")
    assert gc.annotations.read_only_hint is True and gc.input_schema["required"] == ["symbol", "interval"] and gc.meta["platform_mcp/endpoint"] == "/api/v3/klines"
    assert set(SPEC["adapter"]["not_offered"]) == {"get_series", "get_news"}


@pytest.mark.asyncio
@respx.mock
async def test_get_candles_maps_positional_kline_arrays_by_index():
    respx.get(f"{BASE}/api/v3/klines").mock(return_value=httpx.Response(200, json=[KLINE]))
    res = await _server().call_tool("get_candles", {"symbol": "BTCUSDT", "interval": "1h", "start": "1499040000000", "limit": 2})
    assert res.is_error is False
    c = res.structured_content["candles"][0]
    assert c["time"] == "1499040000000" and c["open"] == 0.0163479 and c["high"] == 0.8 and c["low"] == 0.015758 and c["close"] == 0.015771 and c["volume"] == 148976.11427815
    assert c["raw"] == {"values": KLINE}
    q = respx.calls.last.request.url.params
    assert q["symbol"] == "BTCUSDT" and q["interval"] == "1h" and q["startTime"] == "1499040000000" and q["limit"] == "2" and "endTime" not in q


@pytest.mark.asyncio
@respx.mock
async def test_search_symbols_filters_exchange_info_by_symbol():
    respx.get(f"{BASE}/api/v3/exchangeInfo").mock(return_value=httpx.Response(200, json={
        "timezone": "UTC", "serverTime": 1565246363776, "rateLimits": [], "exchangeFilters": [],
        "symbols": [{"symbol": "ETHBTC", "status": "TRADING", "baseAsset": "ETH", "baseAssetPrecision": 8, "quoteAsset": "BTC", "orderTypes": ["LIMIT", "MARKET"], "permissions": ["SPOT"], "filters": []}]}))
    res = await _server().call_tool("search_symbols", {"query": "ETHBTC"})
    assert res.is_error is False
    r = res.structured_content["results"][0]
    assert r["symbol"] == "ETHBTC" and r["name"] == "ETH" and r["type"] == "TRADING"
    assert respx.calls.last.request.url.params["symbol"] == "ETHBTC"


@pytest.mark.asyncio
@respx.mock
async def test_invalid_symbol_400_is_an_is_error_result():
    respx.get(f"{BASE}/api/v3/klines").mock(return_value=httpx.Response(400, json={"code": -1121, "msg": "Invalid symbol."}))
    res = await _server().call_tool("get_candles", {"symbol": "NOPE", "interval": "1h"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input" and "Invalid symbol" in res.structured_content["message"]
