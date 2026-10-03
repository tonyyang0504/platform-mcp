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

SPEC = json.loads((ROOT / "catalog" / "trading" / "luno.json").read_text(encoding="utf-8"))
BASE = "https://api.luno.com"


def _m(mid, base, quote):
    return {"market_id": mid, "trading_status": "ACTIVE", "base_currency": base, "counter_currency": quote, "min_volume": "0.0005",
            "max_volume": "100.00", "volume_scale": 4, "min_price": "10.00", "max_price": "10000000.00", "price_scale": 0, "fee_scale": 8}


# /api/exchange/1/markets answers every market, not sorted by id (live 2026-09-27)
MARKETS = {"markets": [_m("SONICMYR", "SONIC", "MYR"), _m("XBTZAR", "XBT", "ZAR"), _m("ETHZAR", "ETH", "ZAR")]}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
async def test_public_reads_only():
    tools = {t.name: t for t in await _server().list_tools()}
    assert sorted(tools) == ["get_ticker", "list_markets"]
    assert all(t.annotations.read_only_hint for t in tools.values())
    for verb in ("me", "get_candles", "get_balances", "list_orders", "place_order", "cancel_order"):
        assert verb in SPEC["adapter"]["not_offered"]


@pytest.mark.asyncio
@respx.mock
async def test_list_markets_sorts_and_pages_locally():
    route = respx.get(f"{BASE}/api/exchange/1/markets").mock(return_value=httpx.Response(200, json=MARKETS))
    p1 = (await _server().call_tool("list_markets", {"limit": 2})).structured_content
    assert [m["symbol"] for m in p1["markets"]] == ["ETHZAR", "SONICMYR"]
    assert p1["markets"][0]["base"] == "ETH" and p1["markets"][0]["quote"] == "ZAR" and p1["markets"][0]["raw"]["trading_status"] == "ACTIVE"
    assert p1["total"] == 3 and p1["next_page"] == 2
    p2 = (await _server().call_tool("list_markets", {"limit": 2, "page": 2})).structured_content
    assert [m["symbol"] for m in p2["markets"]] == ["XBTZAR"] and p2["next_page"] is None
    assert "pair" not in route.calls.last.request.url.params


@pytest.mark.asyncio
@respx.mock
async def test_get_ticker_maps_string_prices():
    route = respx.get(f"{BASE}/api/1/ticker", params={"pair": "XBTZAR"}).mock(return_value=httpx.Response(200, json={
        "pair": "XBTZAR", "timestamp": 1790516492037, "bid": "1385193.00", "ask": "1385194.00", "last_trade": "1385260.00",
        "rolling_24_hour_volume": "10.817066", "status": "ACTIVE"}))
    t = (await _server().call_tool("get_ticker", {"symbol": "XBTZAR"})).structured_content
    assert (t["symbol"], t["last"], t["bid"], t["ask"], t["volume"]) == ("XBTZAR", 1385260, 1385193, 1385194, 10.817066)
    assert route.calls.last.request.url.params["pair"] == "XBTZAR"


@pytest.mark.asyncio
@respx.mock
async def test_unknown_pair_is_a_tool_error():
    respx.get(f"{BASE}/api/1/ticker").mock(return_value=httpx.Response(400, json={"error": "Market not available", "error_code": "ErrMarketUnavailable"}))
    res = await _server().call_tool("get_ticker", {"symbol": "NOPEZAR"})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error" and "ErrMarketUnavailable" in res.structured_content["message"]
