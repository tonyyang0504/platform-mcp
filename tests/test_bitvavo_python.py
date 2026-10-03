"""Bitvavo (trading, public market data), built through the forge end to end (docs/FORGE_VERIFICATION.md).
Responses shaped like the live API (2026-09-27)."""
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

SPEC = json.loads((ROOT / "catalog" / "trading" / "bitvavo.json").read_text(encoding="utf-8"))
BASE = "https://api.bitvavo.com/v2"
MARKETS = [  # live order is not sorted
    {"market": "FUN-EUR", "status": "trading", "base": "FUN", "quote": "EUR", "minOrderInQuoteAsset": "5.00", "orderTypes": ["market", "limit"]},
    {"market": "BTC-EUR", "status": "trading", "base": "BTC", "quote": "EUR", "minOrderInQuoteAsset": "5.00", "orderTypes": ["market", "limit"]},
    {"market": "ETH-USDC", "status": "halted", "base": "ETH", "quote": "USDC", "minOrderInQuoteAsset": "5.00", "orderTypes": ["market", "limit"]},
    {"market": "ADA-EUR", "status": "trading", "base": "ADA", "quote": "EUR", "minOrderInQuoteAsset": "5.00", "orderTypes": ["market", "limit"]}]
TICKER = {"market": "BTC-EUR", "startTimestamp": 1790437409179, "timestamp": 1790523809179, "open": "73876", "high": "7.479E+4", "low": "73641", "last": "74206",
          "bid": "74209", "bidSize": "0.26939002", "ask": "74210", "askSize": "0.00202141", "volume": "298.00767161", "volumeQuote": "22135858.08095287"}
CANDLES = [[1790521200000, "74243", "74355", "74081", "74211", "20.99724923"], [1790517600000, "74689", "74706", "74171", "74255", "26.47847071"]]


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
async def test_public_reads_only():
    tools = {t.name: t for t in await _server().list_tools()}
    assert sorted(tools) == ["get_candles", "get_ticker", "list_markets"]
    assert all(t.annotations.read_only_hint for t in tools.values())
    assert set(SPEC["adapter"]["not_offered"]) == {"me", "get_balances", "list_orders", "place_order", "cancel_order"}


@pytest.mark.asyncio
@respx.mock
async def test_list_markets_filters_sorts_and_pages_one_download():
    route = respx.get(f"{BASE}/markets").mock(return_value=httpx.Response(200, json=MARKETS))
    s = _server()
    p1 = (await s.call_tool("list_markets", {"limit": 2})).structured_content
    assert [m["symbol"] for m in p1["markets"]] == ["ADA-EUR", "BTC-EUR"] and p1["total"] == 4 and p1["next_page"] == 2
    assert p1["markets"][1] == {"symbol": "BTC-EUR", "base": "BTC", "quote": "EUR", "type": "spot", "raw": MARKETS[1]}
    p2 = (await s.call_tool("list_markets", {"limit": 2, "page": 2})).structured_content
    assert [m["symbol"] for m in p2["markets"]] == ["ETH-USDC", "FUN-EUR"] and p2["next_page"] is None
    q = (await s.call_tool("list_markets", {"query": "usdc"})).structured_content
    assert [m["symbol"] for m in q["markets"]] == ["ETH-USDC"] and q["total"] == 1
    assert route.call_count == 1 and not route.calls.last.request.url.params


@pytest.mark.asyncio
@respx.mock
async def test_get_ticker_sends_market_and_parses_exponent_numbers():
    route = respx.get(f"{BASE}/ticker/24h").mock(return_value=httpx.Response(200, json=TICKER))
    r = (await _server().call_tool("get_ticker", {"symbol": "BTC-EUR"})).structured_content
    assert (r["symbol"], r["last"], r["bid"], r["ask"], r["volume"]) == ("BTC-EUR", 74206, 74209, 74210, 298.00767161)
    assert r["raw"]["high"] == "7.479E+4" and route.calls.last.request.url.params["market"] == "BTC-EUR"


@pytest.mark.asyncio
@respx.mock
async def test_get_candles_maps_positional_rows():
    route = respx.get(f"{BASE}/BTC-EUR/candles").mock(return_value=httpx.Response(200, json=CANDLES))
    r = (await _server().call_tool("get_candles", {"symbol": "BTC-EUR", "interval": "1h", "limit": 2})).structured_content
    assert [(c["time"], c["open"], c["close"], c["volume"]) for c in r["candles"]] == [
        ("2026-09-27T15:00:00Z", 74243, 74211, 20.99724923), ("2026-09-27T14:00:00Z", 74689, 74255, 26.47847071)]
    q = route.calls.last.request.url.params
    assert (q["interval"], q["limit"]) == ("1h", "2")


@pytest.mark.asyncio
@respx.mock
async def test_unknown_market_400_is_invalid_input_and_429_is_rate_limited():
    respx.get(f"{BASE}/ticker/24h").mock(return_value=httpx.Response(400, json={"errorCode": 205, "error": "market parameter is invalid."}))
    r = await _server().call_tool("get_ticker", {"symbol": "ZZZ-EUR"})
    assert r.is_error and (r.structured_content["error"], r.structured_content["http_status"]) == ("invalid_input", 400)
    assert "market parameter is invalid" in r.structured_content["message"]
    respx.get(f"{BASE}/BTC-EUR/candles").mock(return_value=httpx.Response(429, json={"errorCode": 105, "error": "Your IP or API key has been banned for not respecting the rate limit."}))
    r = await _server().call_tool("get_candles", {"symbol": "BTC-EUR", "interval": "1h"})
    assert r.is_error and r.structured_content["error"] == "rate_limited"
