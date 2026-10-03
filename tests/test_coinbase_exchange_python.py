"""Coinbase Exchange public market data (forge stress test 2026-10): l-h-o-c candle rows, ticker without the id."""
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

SPEC = json.loads((ROOT / "catalog" / "trading" / "coinbase_exchange.json").read_text(encoding="utf-8"))
BASE = "https://api.exchange.coinbase.com"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_ticker_and_candles():
    respx.get(f"{BASE}/products/BTC-USD/ticker").mock(return_value=httpx.Response(200, json={"ask": "83942.15", "bid": "83942.14", "volume": "7070.2", "price": "83942.14"}))
    route = respx.get(f"{BASE}/products/BTC-USD/candles").mock(return_value=httpx.Response(200, json=[[1790852400, 83743.11, 84019, 83935.64, 83985.19, 120.7], [1790848800, 1, 2, 1.5, 1.7, 3]]))
    t = (await _server().call_tool("get_ticker", {"symbol": "BTC-USD"})).structured_content
    assert (t["symbol"], t["last"], t["bid"], t["ask"], t["volume"]) == ("BTC-USD", 83942.14, 83942.14, 83942.15, 7070.2)
    c = (await _server().call_tool("get_candles", {"symbol": "BTC-USD", "interval": "1h", "limit": 1})).structured_content["candles"]
    assert len(c) == 1 and (c[0]["low"], c[0]["high"], c[0]["open"], c[0]["close"]) == (83743.11, 84019, 83935.64, 83985.19)
    assert route.calls.last.request.url.params["granularity"] == "3600"


@pytest.mark.asyncio
@respx.mock
async def test_unknown_product_and_granularity():
    respx.get(f"{BASE}/products/NOPE-USD/ticker").mock(return_value=httpx.Response(404, json={"message": "NotFound"}))
    r = await _server().call_tool("get_ticker", {"symbol": "NOPE-USD"})
    assert r.is_error and r.structured_content["error"] == "not_found"
    r = await _server().call_tool("get_candles", {"symbol": "BTC-USD", "interval": "2h"})
    assert r.is_error and r.structured_content["error"] == "invalid_input"
