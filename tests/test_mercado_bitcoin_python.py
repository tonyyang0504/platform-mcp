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

SPEC = json.loads((ROOT / "catalog" / "trading" / "mercado_bitcoin.json").read_text(encoding="utf-8"))
BASE = "https://api.mercadobitcoin.net/api/v4"
# /symbols answers parallel arrays, in no stable order (live 2026-09-27)
SYMBOLS = {"symbol": ["ETH-BRL", "BTC-BRL", "ADA-BRL"], "description": ["Ethereum", "Bitcoin", "Cardano"], "currency": ["BRL", "BRL", "BRL"],
           "base-currency": ["ETH", "BTC", "ADA"], "type": ["CRYPTO", "CRYPTO", "CRYPTO"], "exchange-listed": [True, True, True]}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
async def test_public_reads_only():
    tools = {t.name: t for t in await _server().list_tools()}
    assert sorted(tools) == ["get_candles", "get_ticker", "list_markets"]
    assert all(t.annotations.read_only_hint for t in tools.values())
    assert "place_order" in SPEC["adapter"]["not_offered"]


@pytest.mark.asyncio
@respx.mock
async def test_list_markets_transposes_sorts_and_pages_locally():
    respx.get(f"{BASE}/symbols").mock(return_value=httpx.Response(200, json=SYMBOLS))
    p1 = (await _server().call_tool("list_markets", {"limit": 2})).structured_content
    assert [m["symbol"] for m in p1["markets"]] == ["ADA-BRL", "BTC-BRL"]
    assert p1["markets"][1]["base"] == "BTC" and p1["markets"][1]["quote"] == "BRL" and p1["markets"][1]["raw"]["description"] == "Bitcoin"
    assert p1["total"] == 3 and p1["next_page"] == 2
    p2 = (await _server().call_tool("list_markets", {"limit": 2, "page": 2})).structured_content
    assert [m["symbol"] for m in p2["markets"]] == ["ETH-BRL"] and p2["next_page"] is None
    assert "symbols" not in respx.calls.last.request.url.params


@pytest.mark.asyncio
@respx.mock
async def test_get_ticker_and_unknown_symbol():
    respx.get(f"{BASE}/tickers", params={"symbols": "BTC-BRL"}).mock(return_value=httpx.Response(200, json=[
        {"pair": "BTC-BRL", "high": "442065.00000000", "low": "435801.00000000", "vol": "5.65367181", "last": "441600.00000000", "buy": "441602.00000000", "sell": "441603.00000000", "open": "437008.00000000", "date": 1790513243}]))
    t = (await _server().call_tool("get_ticker", {"symbol": "BTC-BRL"})).structured_content
    assert (t["symbol"], t["last"], t["bid"], t["ask"], t["volume"]) == ("BTC-BRL", 441600, 441602, 441603, 5.65367181)
    respx.get(f"{BASE}/tickers", params={"symbols": "ZZZ-BRL"}).mock(return_value=httpx.Response(200, json=[]))
    res = await _server().call_tool("get_ticker", {"symbol": "ZZZ-BRL"})
    assert res.is_error is True and res.structured_content["error"] == "not_found"


@pytest.mark.asyncio
@respx.mock
async def test_get_candles_transposes_the_udf_arrays():
    route = respx.get(f"{BASE}/candles").mock(return_value=httpx.Response(200, json={
        "t": [1790503200, 1790506800], "o": ["441283.00000000", "440990.00000000"], "h": ["442065.00000000", "441402.00000000"],
        "l": ["440751.00000000", "440863.00000000"], "c": ["441159.00000000", "441150.00000000"], "v": ["0.73424520", "0.13650401"]}))
    res = await _server().call_tool("get_candles", {"symbol": "BTC-BRL", "interval": "1h", "limit": 2})
    assert res.is_error is False
    c = res.structured_content["candles"]
    assert c[0] == {"time": "1790503200", "open": 441283, "high": 442065, "low": 440751, "close": 441159, "volume": 0.7342452, "raw": c[0]["raw"]}
    q = route.calls.last.request.url.params
    assert q["symbol"] == "BTC-BRL" and q["resolution"] == "1h" and q["countback"] == "2" and int(q["to"]) > 1_700_000_000


@pytest.mark.asyncio
@respx.mock
async def test_platform_error_body_is_a_tool_error():
    respx.get(f"{BASE}/candles").mock(return_value=httpx.Response(400, json={"code": "PUBLIC_DATA|LIST_CANDLES|SYMBOL_IS_INVALID", "message": "bad symbol"}))
    res = await _server().call_tool("get_candles", {"symbol": "nope", "interval": "1h"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input" and "SYMBOL_IS_INVALID" in res.structured_content["message"]


@pytest.mark.asyncio
@respx.mock
async def test_list_markets_query_filters_symbol_base_or_quote_and_pages_come_from_one_download():
    route = respx.get(f"{BASE}/symbols").mock(return_value=httpx.Response(200, json=SYMBOLS))
    s = _server()
    r = (await s.call_tool("list_markets", {"query": "btc"})).structured_content
    assert [m["symbol"] for m in r["markets"]] == ["BTC-BRL"] and r["total"] == 1
    r = (await s.call_tool("list_markets", {"query": "brl", "limit": 2, "page": 2})).structured_content
    assert [m["symbol"] for m in r["markets"]] == ["ETH-BRL"] and r["total"] == 3
    assert route.call_count == 1
