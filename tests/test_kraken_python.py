"""Kraken spot public market data (forge stress test 2026-10): error-list envelope, results keyed by Kraken's
internal pair name (`result.*`), OHLC that ignores the page size (`cap: tail`)."""
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

SPEC = json.loads((ROOT / "catalog" / "trading" / "kraken.json").read_text(encoding="utf-8"))
BASE = "https://api.kraken.com/0"
PAIRS = {"error": [], "result": {
    "XXBTZUSD": {"altname": "XBTUSD", "wsname": "XBT/USD", "aclass_base": "currency", "base": "XXBT", "quote": "ZUSD", "status": "online"},
    "XETHZEUR": {"altname": "ETHEUR", "wsname": "ETH/EUR", "aclass_base": "currency", "base": "XETH", "quote": "ZEUR", "status": "online"},
    "AAVEXBT": {"altname": "AAVEXBT", "wsname": "AAVE/XBT", "aclass_base": "currency", "base": "AAVE", "quote": "XXBT", "status": "online"}}}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
async def test_public_reads_only():
    tools = {t.name: t for t in await _server().list_tools()}
    assert sorted(tools) == ["get_candles", "get_ticker", "list_markets"]
    assert all(t.annotations.read_only_hint for t in tools.values())


@pytest.mark.asyncio
@respx.mock
async def test_list_markets_values_sorted_filtered():
    respx.get(f"{BASE}/public/AssetPairs").mock(return_value=httpx.Response(200, json=PAIRS))
    res = (await _server().call_tool("list_markets", {"query": "xbt", "limit": 1})).structured_content
    assert [m["symbol"] for m in res["markets"]] == ["AAVEXBT"] and res["total"] == 2 and res["next_page"] == 2
    assert res["markets"][0]["raw"]["_key"] == "AAVEXBT"


@pytest.mark.asyncio
@respx.mock
async def test_ticker_reads_the_only_result_key():
    route = respx.get(f"{BASE}/public/Ticker").mock(return_value=httpx.Response(200, json={"error": [], "result": {"XXBTZUSD": {
        "a": ["83927.90000", "1", "1.000"], "b": ["83927.80000", "1", "1.000"], "c": ["83927.10000", "0.0001"], "v": ["1175.2", "3280.5"]}}}))
    t = (await _server().call_tool("get_ticker", {"symbol": "XBTUSD"})).structured_content
    assert (t["symbol"], t["last"], t["bid"], t["ask"], t["volume"]) == ("XBTUSD", 83927.1, 83927.8, 83927.9, 3280.5)
    assert route.calls.last.request.url.params["pair"] == "XBTUSD"


@pytest.mark.asyncio
@respx.mock
async def test_candles_keep_the_newest_limit():
    rows = [[1788260400 + 3600 * i, "1.0", "2.0", "0.5", str(i), "1.1", "10.5", 3] for i in range(720)]
    route = respx.get(f"{BASE}/public/OHLC").mock(return_value=httpx.Response(200, json={"error": [], "result": {"XXBTZUSD": rows, "last": 1}}))
    c = (await _server().call_tool("get_candles", {"symbol": "XBTUSD", "interval": "1h", "limit": 2})).structured_content["candles"]
    assert [x["close"] for x in c] == [718, 719] and c[0]["time"] == "2026-10-01T09:00:00Z" and c[0]["volume"] == 10.5
    assert route.calls.last.request.url.params["interval"] == "60"


@pytest.mark.asyncio
@respx.mock
async def test_error_list_is_a_tool_error():
    respx.get(f"{BASE}/public/Ticker").mock(return_value=httpx.Response(200, json={"error": ["EQuery:Unknown asset pair"]}))
    res = await _server().call_tool("get_ticker", {"symbol": "NOPEUSD"})
    assert res.is_error and res.structured_content["error"] == "not_found" and "Unknown asset pair" in res.structured_content["message"]
