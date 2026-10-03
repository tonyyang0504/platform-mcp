"""Coinmate (forge stress test 2026-10, Apiary API Blueprint): {error: true} envelope."""
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

SPEC = json.loads((ROOT / "catalog" / "trading" / "coinmate.json").read_text(encoding="utf-8"))
BASE = "https://coinmate.io/api"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_pairs_and_ticker():
    respx.get(f"{BASE}/tradingPairs").mock(return_value=httpx.Response(200, json={"error": False, "errorMessage": None, "data": [
        {"name": "BTC_EUR", "firstCurrency": "BTC", "secondCurrency": "EUR"}, {"name": "BTC_CZK", "firstCurrency": "BTC", "secondCurrency": "CZK"}]}))
    respx.get(f"{BASE}/ticker").mock(return_value=httpx.Response(200, json={"error": False, "errorMessage": None, "data": {"last": 74236.9, "bid": 74236.8, "ask": 74236.9, "amount": 17.1}}))
    m = (await _server().call_tool("list_markets", {})).structured_content
    assert [x["symbol"] for x in m["markets"]] == ["BTC_CZK", "BTC_EUR"]
    t = (await _server().call_tool("get_ticker", {"symbol": "BTC_EUR"})).structured_content
    assert (t["symbol"], t["last"], t["volume"]) == ("BTC_EUR", 74236.9, 17.1)


@pytest.mark.asyncio
@respx.mock
async def test_error_true_envelope():
    respx.get(f"{BASE}/ticker").mock(return_value=httpx.Response(200, json={"error": True, "errorMessage": "Currency pair NOPE_EUR not found.", "data": None}))
    r = await _server().call_tool("get_ticker", {"symbol": "NOPE_EUR"})
    assert r.is_error and r.structured_content["error"] == "not_found" and "NOPE_EUR" in r.structured_content["message"]
