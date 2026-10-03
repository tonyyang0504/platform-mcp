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

SPEC = json.loads((ROOT / "catalog" / "market_data" / "bybit_collector.json").read_text(encoding="utf-8"))
BASE = "https://api.bybit.com"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_market_data_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_candles", "me", "search_symbols"]
    gc = next(t for t in tools if t.name == "get_candles")
    assert gc.annotations.read_only_hint is True and gc.meta["platform_mcp/endpoint"] == "/v5/market/kline"


@pytest.mark.asyncio
@respx.mock
async def test_get_candles_maps_result_list_rows_by_index():
    # bybit-exchange.github.io/docs/v5/market/kline: list rows [startTime, open, high, low, close, volume, turnover]
    respx.get(f"{BASE}/v5/market/kline").mock(return_value=httpx.Response(200, json={
        "retCode": 0, "retMsg": "OK", "result": {"category": "linear", "symbol": "BTCUSDT", "list": [
            ["1670608800000", "17071", "17073", "17027", "17055.5", "268611", "15.74462667"],
            ["1670605200000", "17071.5", "17073", "17061", "17071", "4177", "0.24469757"]]}, "retExtInfo": {}, "time": 1672025956592}))
    res = await _server().call_tool("get_candles", {"symbol": "BTCUSDT", "interval": "60", "start": "1670601600000", "end": "1670608800000", "limit": 2})
    assert res.is_error is False
    c = res.structured_content["candles"][0]
    assert c["time"] == "1670608800000" and c["open"] == 17071 and c["high"] == 17073 and c["low"] == 17027 and c["close"] == 17055.5 and c["volume"] == 268611
    q = respx.calls.last.request.url.params
    assert q["category"] == "linear" and q["symbol"] == "BTCUSDT" and q["interval"] == "60" and q["start"] == "1670601600000" and q["end"] == "1670608800000" and q["limit"] == "2"


@pytest.mark.asyncio
@respx.mock
async def test_search_symbols_lists_linear_instruments():
    respx.get(f"{BASE}/v5/market/instruments-info").mock(return_value=httpx.Response(200, json={
        "retCode": 0, "retMsg": "OK", "result": {"category": "linear", "list": [
            {"symbol": "BTCUSDT", "contractType": "LinearPerpetual", "status": "Trading", "baseCoin": "BTC", "quoteCoin": "USDT", "launchTime": "1585526400000",
             "priceFilter": {"minPrice": "0.10", "maxPrice": "199999.80", "tickSize": "0.10"}, "lotSizeFilter": {"maxOrderQty": "1190.000", "minOrderQty": "0.001", "qtyStep": "0.001"}}],
            "nextPageCursor": ""}, "time": 1672712495660}))
    res = await _server().call_tool("search_symbols", {"query": "BTCUSDT"})
    assert res.is_error is False
    r = res.structured_content["results"][0]
    assert r["symbol"] == "BTCUSDT" and r["name"] == "BTC" and r["type"] == "LinearPerpetual"
    q = respx.calls.last.request.url.params
    assert q["category"] == "linear" and q["symbol"] == "BTCUSDT"


@pytest.mark.asyncio
@respx.mock
async def test_ip_ban_403_is_an_error_result():
    respx.get(f"{BASE}/v5/market/time").mock(return_value=httpx.Response(403, text="access too frequent"))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 403
