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

SPEC = json.loads((ROOT / "catalog" / "trading" / "hyperliquid.json").read_text(encoding="utf-8"))


WALLET = "0x1111111111111111111111111111111111111111"


def _server(creds=None):
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], creds or {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_public_read_verbs_are_offered():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_ticker", "list_markets", "list_orders", "me"]
    assert all(t.annotations.read_only_hint is True for t in tools)
    lm = next(t for t in tools if t.name == "list_markets")
    assert lm.meta["platform_mcp/endpoint"] == "/info" and lm.output_schema["properties"]["markets"]["type"] == "array"
    assert set(SPEC["adapter"]["not_offered"]) == {"get_candles", "get_balances", "place_order", "cancel_order"}
    assert "EIP-712" in SPEC["adapter"]["not_offered"]["place_order"]


@pytest.mark.asyncio
@respx.mock
async def test_list_markets_posts_the_typed_meta_body():
    # hyperliquid-docs info-endpoint/perpetuals: POST /info {"type": "meta"} -> {universe: [{name, szDecimals, maxLeverage}], marginTables}
    route = respx.post("https://api.hyperliquid.xyz/info").mock(return_value=httpx.Response(200, json={
        "universe": [{"name": "BTC", "szDecimals": 5, "maxLeverage": 50}, {"name": "ETH", "szDecimals": 4, "maxLeverage": 50}],
        "marginTables": [[50, {"description": "", "marginTiers": [{"lowerBound": "0.0", "maxLeverage": 50}]}]]}))
    res = await _server().call_tool("list_markets", {})
    assert res.is_error is False
    sc = res.structured_content
    assert [m["symbol"] for m in sc["markets"]] == ["BTC", "ETH"] and sc["markets"][0]["max_leverage"] == 50 and sc["next_page"] is None
    req = route.calls.last.request
    assert json.loads(req.content) == {"type": "meta"} and req.headers["content-type"] == "application/json"


@pytest.mark.asyncio
@respx.mock
async def test_get_ticker_reads_top_of_book_from_l2book():
    route = respx.post("https://api.hyperliquid.xyz/info").mock(return_value=httpx.Response(200, json={
        "coin": "BTC", "time": 1754450974231,
        "levels": [[{"px": "113377.0", "sz": "7.6699", "n": 17}, {"px": "113376.0", "sz": "4.13714", "n": 8}], [{"px": "113397.0", "sz": "0.11543", "n": 3}]]}))
    res = await _server().call_tool("get_ticker", {"symbol": "BTC"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["symbol"] == "BTC" and sc["bid"] == 113377 and sc["ask"] == 113397 and sc["bid_size"] == 7.6699  # numbers, as the vocabulary types bid/ask
    assert json.loads(route.calls.last.request.content) == {"type": "l2Book", "coin": "BTC"}


@pytest.mark.asyncio
@respx.mock
async def test_upstream_failure_is_an_is_error_result():
    respx.post("https://api.hyperliquid.xyz/info").mock(return_value=httpx.Response(500, text="internal"))
    res = await _server().call_tool("get_ticker", {"symbol": "BTC"})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error" and res.structured_content["http_status"] == 500


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_reads_open_orders_of_the_configured_public_address():
    # info-endpoint: {"type": "openOrders", "user": "0x..."} -> [{coin, limitPx, oid, side, sz, timestamp}]
    route = respx.post("https://api.hyperliquid.xyz/info").mock(return_value=httpx.Response(200, json=[
        {"coin": "BTC", "limitPx": "29792.0", "oid": 91490942, "side": "A", "sz": "0.0", "timestamp": 1681247412573}]))
    res = await _server({"wallet_address": WALLET}).call_tool("list_orders", {})
    assert res.is_error is False
    o = res.structured_content["orders"][0]
    assert o["order_id"] == "91490942" and o["symbol"] == "BTC" and o["side"] == "A" and o["price"] == "29792.0"
    assert json.loads(route.calls.last.request.content) == {"type": "openOrders", "user": WALLET}
