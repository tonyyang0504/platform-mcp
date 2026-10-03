import hashlib
import hmac
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

SPEC = json.loads((ROOT / "catalog" / "trading" / "binance.json").read_text(encoding="utf-8"))
CREDS = {"api_key": "KEY-binance-abcdef", "api_secret": "SECRET-binance-abcdef"}
BASE = "https://fapi.binance.com"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


def _signed(req):
    query = req.url.query.decode()
    signed, _, sig = query.rpartition("&signature=")
    assert sig == hmac.new(CREDS["api_secret"].encode(), signed.encode(), hashlib.sha256).hexdigest()
    assert req.headers["X-MBX-APIKEY"] == CREDS["api_key"] and CREDS["api_secret"] not in str(req.url)
    return dict(p.split("=", 1) for p in signed.split("&"))


@pytest.mark.asyncio
async def test_every_trading_verb_is_offered_and_writes_are_destructive():
    tools = {t.name: t for t in await _server().list_tools()}
    assert sorted(tools) == ["cancel_order", "get_balances", "get_candles", "get_ticker", "list_markets", "list_orders", "me", "place_order"]
    assert tools["place_order"].annotations.destructive_hint is True and tools["get_candles"].annotations.read_only_hint is True
    assert "REAL ORDER WITH REAL FUNDS" in tools["place_order"].description and "testnet.binancefuture.com" in tools["place_order"].description
    assert SPEC["adapter"]["base_url"] == BASE and SPEC["adapter"]["not_offered"] == {}


@pytest.mark.asyncio
@respx.mock
async def test_klines_are_signed_and_mapped_from_positional_rows():
    # futures market data accepts the extra timestamp/signature parameters (unlike spot)
    route = respx.get(url__startswith=f"{BASE}/fapi/v1/klines").mock(return_value=httpx.Response(200, json=[
        [1790262000000, "83628.20", "83810.60", "83440.40", "83769.50", "2526.082", 1790265599999, "211218971.36", 54075, "1272.084", "106402198.73", "0"]]))
    res = await _server().call_tool("get_candles", {"symbol": "BTCUSDT", "interval": "1h", "limit": 5000})
    assert res.is_error is False
    c = res.structured_content["candles"][0]
    assert (c["time"], c["open"], c["high"], c["low"], c["close"], c["volume"]) == ("1790262000000", 83628.2, 83810.6, 83440.4, 83769.5, 2526.082)  # live check 2026-09-26: numbers and a string time, as the vocabulary types them
    params = _signed(route.calls[0].request)
    assert params["symbol"] == "BTCUSDT" and params["interval"] == "1h" and params["limit"] == "1000"  # capped by max_limit


@pytest.mark.asyncio
@respx.mock
async def test_place_order_sends_signed_query_and_balance_maps_assets():
    order = respx.post(url__startswith=f"{BASE}/fapi/v1/order").mock(return_value=httpx.Response(200, json={
        "clientOrderId": "testOrder", "cumQty": "0", "executedQty": "0", "orderId": 22542179, "origQty": "10", "price": "60000", "side": "SELL",
        "positionSide": "BOTH", "status": "NEW", "symbol": "BTCUSDT", "timeInForce": "GTC", "type": "LIMIT"}))
    res = await _server().call_tool("place_order", {"symbol": "BTCUSDT", "side": "sell", "type": "limit", "quantity": 10, "price": 60000})
    assert res.is_error is False and res.structured_content["order_id"] == "22542179" and res.structured_content["status"] == "NEW"
    params = _signed(order.calls[0].request)
    assert {k: params[k] for k in ("symbol", "side", "type", "timeInForce", "quantity", "price")} == {
        "symbol": "BTCUSDT", "side": "SELL", "type": "LIMIT", "timeInForce": "GTC", "quantity": "10", "price": "60000"}
    respx.get(url__startswith=f"{BASE}/fapi/v3/balance").mock(return_value=httpx.Response(200, json=[
        {"accountAlias": "SgsR", "asset": "USDT", "balance": "122.35", "crossWalletBalance": "23.72", "crossUnPnl": "0.00", "availableBalance": "23.72", "updateTime": 1617939110373}]))
    bal = await _server().call_tool("get_balances", {})
    assert bal.structured_content["balances"][0]["asset"] == "USDT" and bal.structured_content["balances"][0]["available"] == "23.72"


@pytest.mark.asyncio
@respx.mock
async def test_error_body_is_an_upstream_error_and_secrets_are_redacted():
    respx.delete(url__startswith=f"{BASE}/fapi/v1/order").mock(return_value=httpx.Response(400, json={"code": -2011, "msg": f"Unknown order sent. {CREDS['api_secret']}"}))
    res = await _server().call_tool("cancel_order", {"order_id": "1", "symbol": "BTCUSDT"})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error"
    assert "Unknown order sent" in res.content[0].text and CREDS["api_secret"] not in res.content[0].text
