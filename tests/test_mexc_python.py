"""MEXC spot (forge stress test 2026-10): mapped from the vendor's Postman collection; the hour interval is 60m."""
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

SPEC = json.loads((ROOT / "catalog" / "trading" / "mexc.json").read_text(encoding="utf-8"))
BASE = "https://api.mexc.com"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_markets_ticker_klines():
    respx.get(f"{BASE}/api/v3/exchangeInfo").mock(return_value=httpx.Response(200, json={"symbols": [
        {"symbol": "ETHUSDT", "baseAsset": "ETH", "quoteAsset": "USDT", "fullName": "Ethereum"},
        {"symbol": "BTCUSDT", "baseAsset": "BTC", "quoteAsset": "USDT", "fullName": "Bitcoin"}]}))
    respx.get(f"{BASE}/api/v3/ticker/24hr").mock(return_value=httpx.Response(200, json={"symbol": "BTCUSDT", "lastPrice": "83954.13", "bidPrice": "83954.1", "askPrice": "83954.2", "volume": "1234.5"}))
    k = respx.get(f"{BASE}/api/v3/klines").mock(return_value=httpx.Response(200, json=[[1790848800000, "83779.12", "84075.96", "83412.21", "83954.13", "235.3", 1790852400000, "19711510.36"]]))
    m = (await _server().call_tool("list_markets", {"query": "bitcoin"})).structured_content
    assert [x["symbol"] for x in m["markets"]] == ["BTCUSDT"]
    t = (await _server().call_tool("get_ticker", {"symbol": "BTCUSDT"})).structured_content
    assert (t["last"], t["bid"], t["ask"], t["volume"]) == (83954.13, 83954.1, 83954.2, 1234.5)
    c = (await _server().call_tool("get_candles", {"symbol": "BTCUSDT", "interval": "1h", "limit": 1})).structured_content["candles"]
    assert c[0]["time"] == "2026-10-01T10:00:00Z" and c[0]["close"] == 83954.13
    assert k.calls.last.request.url.params["interval"] == "60m" and k.calls.last.request.url.params["limit"] == "1"


@pytest.mark.asyncio
@respx.mock
async def test_invalid_symbol():
    respx.get(f"{BASE}/api/v3/ticker/24hr").mock(return_value=httpx.Response(400, json={"msg": "invalid symbol", "code": -1121}))
    r = await _server().call_tool("get_ticker", {"symbol": "NOPEUSDT"})
    assert r.is_error and r.structured_content["error"] == "invalid_input"
