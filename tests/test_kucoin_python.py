"""KuCoin public market data (forge stress test 2026-10): code "200000" envelope, an unknown symbol answered as a
success with every field null (fail_when null must match an explicit null only), candle rows in o-c-h-l order."""
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

SPEC = json.loads((ROOT / "catalog" / "trading" / "kucoin.json").read_text(encoding="utf-8"))
BASE = "https://api.kucoin.com"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_symbols_list_is_not_failed_by_the_null_rule():
    respx.get(f"{BASE}/api/v2/symbols").mock(return_value=httpx.Response(200, json={"code": "200000", "data": [
        {"symbol": "ETH-USDT", "baseCurrency": "ETH", "quoteCurrency": "USDT", "market": "USDS"},
        {"symbol": "BTC-USDT", "baseCurrency": "BTC", "quoteCurrency": "USDT", "market": "USDS"}]}))
    r = await _server().call_tool("list_markets", {"limit": 5})
    assert not r.is_error, r.structured_content
    assert [m["symbol"] for m in r.structured_content["markets"]] == ["BTC-USDT", "ETH-USDT"]


@pytest.mark.asyncio
@respx.mock
async def test_unknown_symbol_all_null_stats_is_not_found():
    respx.get(f"{BASE}/api/v1/market/stats").mock(return_value=httpx.Response(200, json={"code": "200000", "data": {
        "time": 1790855356764, "symbol": "NOPE-USDT", "buy": None, "sell": None, "vol": None, "last": None}}))
    r = await _server().call_tool("get_ticker", {"symbol": "NOPE-USDT"})
    assert r.is_error and r.structured_content["error"] == "not_found" and r.structured_content["message"] == "data.last is null"


@pytest.mark.asyncio
@respx.mock
async def test_candles_open_close_high_low_order():
    route = respx.get(f"{BASE}/api/v1/market/candles").mock(return_value=httpx.Response(200, json={"code": "200000", "data": [
        ["1790852400", "83965.5", "83989.1", "84033.1", "83788.2", "51.2", "4296825.9"],
        ["1790848800", "83772.2", "83968.7", "84091.2", "83423.8", "89.9", "7530787.5"]]}))
    c = (await _server().call_tool("get_candles", {"symbol": "BTC-USDT", "interval": "1h", "limit": 1})).structured_content["candles"]
    assert c == [{"time": "2026-10-01T11:00:00Z", "open": 83965.5, "close": 83989.1, "high": 84033.1, "low": 83788.2, "volume": 51.2,
                  "raw": {"values": ["1790852400", "83965.5", "83989.1", "84033.1", "83788.2", "51.2", "4296825.9"]}}]
    assert route.calls.last.request.url.params["type"] == "1hour"


@pytest.mark.asyncio
@respx.mock
async def test_envelope_failure():
    respx.get(f"{BASE}/api/v1/market/candles").mock(return_value=httpx.Response(200, json={"msg": "Unsupported trading pair.", "code": "400100"}))
    r = await _server().call_tool("get_candles", {"symbol": "NOPE-USDT", "interval": "1h"})
    assert r.is_error and r.structured_content["error"] == "not_found"
