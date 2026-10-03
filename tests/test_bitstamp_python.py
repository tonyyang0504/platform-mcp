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

SPEC = json.loads((ROOT / "catalog" / "trading" / "bitstamp.json").read_text(encoding="utf-8"))
BASE = "https://www.bitstamp.net/api/v2"


def _market(sym, base, quote):
    return {"name": f"{base}/{quote}", "market_symbol": sym, "base_currency": base, "base_decimals": 8, "counter_currency": quote,
            "counter_decimals": 2, "minimum_order_value": "10.00", "trading": "Enabled", "instant_order_counter_decimals": 2,
            "instant_and_market_orders": "Enabled", "description": f"{base} / {quote}", "market_type": "SPOT"}


# /markets/ answers every market at once, not sorted by symbol (live 2026-09-27: eurusd, gbpusd, sgdusd, bchusd, …)
MARKETS = [_market("eurusd", "EUR", "USD"), _market("btcusd", "BTC", "USD"), _market("aaveeur", "AAVE", "EUR")]


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
async def test_public_reads_only():
    tools = {t.name: t for t in await _server().list_tools()}
    assert sorted(tools) == ["get_candles", "get_ticker", "list_markets"]
    assert all(t.annotations.read_only_hint for t in tools.values())
    assert {"me", "get_balances", "list_orders", "place_order", "cancel_order"} <= set(SPEC["adapter"]["not_offered"])


@pytest.mark.asyncio
@respx.mock
async def test_list_markets_sorts_and_pages_locally():
    route = respx.get(f"{BASE}/markets/").mock(return_value=httpx.Response(200, json=MARKETS))
    p1 = (await _server().call_tool("list_markets", {"limit": 2})).structured_content
    assert [m["symbol"] for m in p1["markets"]] == ["aaveeur", "btcusd"]
    assert (p1["markets"][1]["base"], p1["markets"][1]["quote"], p1["markets"][1]["type"]) == ("BTC", "USD", "SPOT")
    assert p1["total"] == 3 and p1["next_page"] == 2
    p2 = (await _server().call_tool("list_markets", {"limit": 2, "page": 2})).structured_content
    assert [m["symbol"] for m in p2["markets"]] == ["eurusd"] and p2["next_page"] is None
    assert dict(route.calls.last.request.url.params) == {}


@pytest.mark.asyncio
@respx.mock
async def test_get_ticker_echoes_symbol_and_parses_numbers():
    respx.get(f"{BASE}/ticker/btcusd/").mock(return_value=httpx.Response(200, json={
        "timestamp": "1790515990", "open": "84433.05", "high": "85089.89", "low": "83825.01", "last": "85052.34", "volume": "591.21243491",
        "vwap": "84407.94", "bid": "85052.33", "ask": "85052.34", "side": "0", "open_24": "83889.59", "percent_change_24": "1.39", "market_type": "SPOT"}))
    t = (await _server().call_tool("get_ticker", {"symbol": "btcusd"})).structured_content
    assert (t["symbol"], t["last"], t["bid"], t["ask"], t["volume"]) == ("btcusd", 85052.34, 85052.33, 85052.34, 591.21243491)


@pytest.mark.asyncio
@respx.mock
async def test_get_candles_maps_interval_to_step():
    route = respx.get(f"{BASE}/ohlc/btcusd/").mock(return_value=httpx.Response(200, json={"data": {"pair": "BTC/USD", "ohlc": [
        {"timestamp": "1790506800", "open": "84858.10", "high": "84934.09", "low": "84819.11", "close": "84878.71", "volume": "8.50015357"},
        {"timestamp": "1790510400", "open": "84878.71", "high": "85016.81", "low": "84794.32", "close": "84794.68", "volume": "21.85591219"}]}}))
    res = await _server().call_tool("get_candles", {"symbol": "btcusd", "interval": "1h", "limit": 2})
    assert res.is_error is False
    c = res.structured_content["candles"]
    assert (c[0]["time"], c[0]["open"], c[0]["high"], c[0]["low"], c[0]["close"], c[0]["volume"]) == (
        "2026-09-27T11:00:00Z", 84858.1, 84934.09, 84819.11, 84878.71, 8.50015357)
    q = route.calls.last.request.url.params
    assert q["step"] == "3600" and q["limit"] == "2"


@pytest.mark.asyncio
async def test_unknown_interval_is_invalid_input():
    res = await _server().call_tool("get_candles", {"symbol": "btcusd", "interval": "7m"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input"


@pytest.mark.asyncio
@respx.mock
async def test_unknown_market_is_a_clean_error():
    respx.get(f"{BASE}/ohlc/nosuchpair/").mock(return_value=httpx.Response(404, text="Not found"))
    res = await _server().call_tool("get_candles", {"symbol": "nosuchpair", "interval": "1h"})
    assert res.is_error is True and res.structured_content["error"] == "not_found"
