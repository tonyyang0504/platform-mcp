"""Upbit quotation API (forge stress test 2026-10, Korean docs): ticker as a one-element list, candle path chosen by
the interval (map: in path_params), zone-less UTC times."""
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

SPEC = json.loads((ROOT / "catalog" / "trading" / "upbit.json").read_text(encoding="utf-8"))
BASE = "https://api.upbit.com"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_markets_filter_on_korean_name():
    respx.get(f"{BASE}/v1/market/all").mock(return_value=httpx.Response(200, json=[
        {"market": "KRW-BTC", "korean_name": "비트코인", "english_name": "Bitcoin"},
        {"market": "KRW-ETH", "korean_name": "이더리움", "english_name": "Ethereum"}]))
    r = (await _server().call_tool("list_markets", {"query": "비트코인"})).structured_content
    assert [m["symbol"] for m in r["markets"]] == ["KRW-BTC"]


@pytest.mark.asyncio
@respx.mock
async def test_ticker_and_candles():
    respx.get(f"{BASE}/v1/ticker").mock(return_value=httpx.Response(200, json=[{"market": "KRW-BTC", "trade_price": 114386000.0, "acc_trade_volume_24h": 1060.4}]))
    route = respx.get(f"{BASE}/v1/candles/minutes/60").mock(return_value=httpx.Response(200, json=[
        {"market": "KRW-BTC", "candle_date_time_utc": "2026-10-01T11:00:00", "opening_price": 1.0, "high_price": 2.0, "low_price": 0.5, "trade_price": 1.5, "candle_acc_trade_volume": 21.5}]))
    t = (await _server().call_tool("get_ticker", {"symbol": "KRW-BTC"})).structured_content
    assert (t["symbol"], t["last"], t["volume"]) == ("KRW-BTC", 114386000.0, 1060.4)
    c = (await _server().call_tool("get_candles", {"symbol": "KRW-BTC", "interval": "1h", "limit": 2})).structured_content["candles"]
    assert c[0]["time"] == "2026-10-01T11:00:00Z" and c[0]["close"] == 1.5
    assert route.calls.last.request.url.params["count"] == "2"


@pytest.mark.asyncio
@respx.mock
async def test_unknown_market():
    respx.get(f"{BASE}/v1/ticker").mock(return_value=httpx.Response(404, json={"error": {"name": 404, "message": "Code not found"}}))
    r = await _server().call_tool("get_ticker", {"symbol": "KRW-NOPE"})
    assert r.is_error and r.structured_content["error"] == "not_found"
    bad = await _server().call_tool("get_candles", {"symbol": "KRW-BTC", "interval": "2h"})
    assert bad.is_error and bad.structured_content["error"] == "invalid_input"
