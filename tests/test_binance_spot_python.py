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

SPEC = json.loads((ROOT / "catalog" / "trading" / "binance_spot.json").read_text(encoding="utf-8"))
CREDS = {"api_key": "KEY-binance-abcdef", "api_secret": "SECRET-binance-abcdef"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _check_signature(req):
    query = req.url.query.decode()
    signed, _, sig = query.rpartition("&signature=")
    assert "&timestamp=" in "&" + signed or signed.startswith("timestamp=")
    assert sig == hmac.new(CREDS["api_secret"].encode(), signed.encode(), hashlib.sha256).hexdigest()
    assert req.headers["X-MBX-APIKEY"] == CREDS["api_key"] and CREDS["api_secret"] not in str(req.url)
    return dict(p.split("=", 1) for p in signed.split("&"))


@pytest.mark.asyncio
async def test_signed_account_and_trading_verbs_are_offered():
    tools = {t.name: t for t in await _server().list_tools()}
    assert sorted(tools) == ["cancel_order", "get_balances", "get_candles", "get_ticker", "list_markets", "list_orders", "me", "place_order"]
    assert tools["place_order"].annotations.destructive_hint is True and tools["cancel_order"].annotations.destructive_hint is True
    assert "REAL ORDER WITH REAL FUNDS" in tools["place_order"].description and "testnet.binance.vision" in tools["place_order"].description
    # public market data rejects extra params (-1104): those tools opt out of signing
    assert SPEC["adapter"]["not_offered"] == {} and all(SPEC["adapter"]["tools"][v]["sign"] is False for v in ("list_markets", "get_ticker", "get_candles"))


@pytest.mark.asyncio
@respx.mock
async def test_get_balances_signs_the_query_with_hmac_sha256():
    # developers.binance.com account-endpoints: GET /api/v3/account (USER_DATA) -> balances[{asset, free, locked}]
    route = respx.get(url__startswith="https://api.binance.com/api/v3/account").mock(return_value=httpx.Response(200, json={
        "makerCommission": 15, "canTrade": True, "canWithdraw": False, "accountType": "SPOT",
        "balances": [{"asset": "BTC", "free": "0.50000000", "locked": "0.10000000"}, {"asset": "USDT", "free": "1200.00000000", "locked": "0.00000000"}],
        "permissions": ["SPOT"]}))
    res = await _server().call_tool("get_balances", {})
    assert res.is_error is False
    assert [(b["asset"], b["free"], b["locked"]) for b in res.structured_content["balances"]] == [("BTC", "0.50000000", "0.10000000"), ("USDT", "1200.00000000", "0.00000000")]
    params = _check_signature(route.calls[0].request)
    assert params["omitZeroBalances"] == "true"


@pytest.mark.asyncio
@respx.mock
async def test_place_limit_and_market_orders_send_signed_query_parameters():
    # trading-endpoints: POST /api/v3/order; LIMIT needs timeInForce, quantity, price; MARKET needs quantity
    route = respx.post(url__startswith="https://api.binance.com/api/v3/order").mock(return_value=httpx.Response(200, json={
        "symbol": "BTCUSDT", "orderId": 28, "orderListId": -1, "clientOrderId": "6gCrw2kRUAF9CvJDGP16IP", "transactTime": 1507725176595,
        "price": "65000.50000000", "origQty": "0.01000000", "executedQty": "0.00000000", "status": "NEW", "timeInForce": "GTC", "type": "LIMIT", "side": "BUY"}))
    server = _server()
    res = await server.call_tool("place_order", {"symbol": "BTCUSDT", "side": "buy", "type": "limit", "quantity": 0.01, "price": 65000.5})
    assert res.is_error is False
    assert res.structured_content["order_id"] == "28" and res.structured_content["status"] == "NEW"
    req = route.calls[0].request
    assert req.method == "POST" and req.content == b""
    params = _check_signature(req)
    assert {k: params[k] for k in ("symbol", "side", "type", "timeInForce", "quantity", "price")} == {
        "symbol": "BTCUSDT", "side": "BUY", "type": "LIMIT", "timeInForce": "GTC", "quantity": "0.01", "price": "65000.5"}
    await server.call_tool("place_order", {"symbol": "BTCUSDT", "side": "sell", "type": "market", "quantity": 1})
    params = _check_signature(route.calls[1].request)
    assert params["side"] == "SELL" and params["type"] == "MARKET" and params["quantity"] == "1"
    assert "timeInForce" not in params and "price" not in params


@pytest.mark.asyncio
@respx.mock
async def test_cancel_order_is_a_signed_delete_and_bad_side_never_reaches_binance():
    route = respx.delete(url__startswith="https://api.binance.com/api/v3/order").mock(return_value=httpx.Response(200, json={
        "symbol": "LTCBTC", "origClientOrderId": "myOrder1", "orderId": 4, "status": "CANCELED"}))
    res = await _server().call_tool("cancel_order", {"order_id": "4", "symbol": "LTCBTC"})
    assert res.is_error is False and res.structured_content["status"] == "CANCELED" and res.structured_content["order_id"] == "4"
    params = _check_signature(route.calls[0].request)
    assert params["symbol"] == "LTCBTC" and params["orderId"] == "4"
    bad = await _server().call_tool("place_order", {"symbol": "BTCUSDT", "side": "hold", "type": "market", "quantity": 1})
    assert bad.is_error is True and bad.structured_content["error"] == "invalid_input" and route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_rejected_order_is_an_error_without_leaking_the_secret():
    respx.post(url__startswith="https://api.binance.com/api/v3/order").mock(return_value=httpx.Response(400, json={
        "code": -2010, "msg": f"Account has insufficient balance for requested action. key={CREDS['api_key']} secret {CREDS['api_secret']}"}))
    res = await _server().call_tool("place_order", {"symbol": "BTCUSDT", "side": "buy", "type": "market", "quantity": 5})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error"
    text = res.content[0].text
    assert "insufficient balance" in text and CREDS["api_secret"] not in text and CREDS["api_key"] not in text


@pytest.mark.asyncio
@respx.mock
async def test_public_market_data_is_sent_unsigned():
    # market-data-endpoints: GET /api/v3/klines, GET /api/v3/ticker/24hr (security type NONE; extra params -> -1104)
    kl = respx.get(url__startswith="https://api.binance.com/api/v3/klines").mock(return_value=httpx.Response(200, json=[
        [1499040000000, "0.01634790", "0.80000000", "0.01575800", "0.01577100", "148976.11427815", 1499644799999, "2434.19055334", 308, "1756.87402397", "28.46694368", "0"]]))
    res = await _server().call_tool("get_candles", {"symbol": "BNBBTC", "interval": "1d", "limit": 5000})
    assert res.is_error is False
    c = res.structured_content["candles"][0]
    assert (c["time"], c["open"], c["high"], c["low"], c["close"], c["volume"]) == ("1499040000000", 0.0163479, 0.8, 0.015758, 0.015771, 148976.11427815)
    params = dict(kl.calls[0].request.url.params)
    assert params == {"symbol": "BNBBTC", "interval": "1d", "limit": "1000"}
    tk = respx.get(url__startswith="https://api.binance.com/api/v3/ticker/24hr").mock(return_value=httpx.Response(200, json={
        "symbol": "BNBBTC", "lastPrice": "4.00000200", "bidPrice": "4.00000000", "askPrice": "4.00000200", "volume": "8913.30000000"}))
    t = await _server().call_tool("get_ticker", {"symbol": "BNBBTC"})
    assert t.structured_content["last"] == "4.00000200" and t.structured_content["bid"] == "4.00000000"
    q = tk.calls[0].request.url.query.decode()
    assert q == "symbol=BNBBTC" and "signature" not in q and "timestamp" not in q
    respx.get(url__startswith="https://api.binance.com/api/v3/exchangeInfo").mock(return_value=httpx.Response(200, json={
        "timezone": "UTC", "symbols": [{"symbol": "ETHBTC", "status": "TRADING", "baseAsset": "ETH", "quoteAsset": "BTC"}]}))
    m = await _server().call_tool("list_markets", {})
    assert m.structured_content["markets"][0]["base"] == "ETH" and "signature" not in str(respx.calls.last.request.url)
