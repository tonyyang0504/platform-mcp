"""Gemini public market data (forge stress test 2026-10): a bare list of strings (`scalar_rows`), a volume keyed by the
base currency (`volume.*`), candles newest first that ignore any count (`cap: head`)."""
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

SPEC = json.loads((ROOT / "catalog" / "trading" / "gemini.json").read_text(encoding="utf-8"))
BASE = "https://api.gemini.com"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_symbols_list_of_strings():
    respx.get(f"{BASE}/v1/symbols").mock(return_value=httpx.Response(200, json=["ethusd", "btcusd", "btceur", "solusd"]))
    r = (await _server().call_tool("list_markets", {"query": "btc", "limit": 1})).structured_content
    assert r["markets"] == [{"symbol": "btceur", "raw": {"values": "btceur"}}] and r["total"] == 2 and r["next_page"] == 2


@pytest.mark.asyncio
@respx.mock
async def test_ticker_volume_in_base_currency():
    respx.get(f"{BASE}/v1/pubticker/btcusd").mock(return_value=httpx.Response(200, json={
        "bid": "83951.63000", "ask": "83951.64000", "last": "83962.95000", "volume": {"BTC": "145.5977532", "USD": "12224816.87", "timestamp": 1790855160000}}))
    t = (await _server().call_tool("get_ticker", {"symbol": "btcusd"})).structured_content
    assert (t["symbol"], t["last"], t["bid"], t["ask"], t["volume"]) == ("btcusd", 83962.95, 83951.63, 83951.64, 145.5977532)


@pytest.mark.asyncio
@respx.mock
async def test_candles_newest_first_capped():
    rows = [[1790848800000 - 3600000 * i, 1.5, 2, 1, 1.75, 0.5] for i in range(50)]
    route = respx.get(f"{BASE}/v2/candles/btcusd/1hr").mock(return_value=httpx.Response(200, json=rows))
    c = (await _server().call_tool("get_candles", {"symbol": "btcusd", "interval": "1hr", "limit": 3})).structured_content["candles"]
    assert len(c) == 3 and c[0]["time"] == "2026-10-01T10:00:00Z" and c[0]["close"] == 1.75 and route.called


@pytest.mark.asyncio
@respx.mock
async def test_unknown_symbol_not_found():
    respx.get(f"{BASE}/v1/pubticker/nopeusd").mock(return_value=httpx.Response(404, json={"result": "error", "reason": "InvalidSymbol", "message": "'nopeusd' does not have available data yet"}))
    r = await _server().call_tool("get_ticker", {"symbol": "nopeusd"})
    assert r.is_error and r.structured_content["error"] == "not_found"
