import base64
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

SPEC = json.loads((ROOT / "catalog" / "trading" / "deribit.json").read_text(encoding="utf-8"))
CREDS = {"client_id": "CID-deribit-abc", "client_secret": "SECRET-deribit-abcdef"}
BASE = "https://www.deribit.com/api/v2"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


@pytest.mark.asyncio
async def test_verbs_and_candles_not_offered():
    tools = {t.name: t for t in await _server().list_tools()}
    assert sorted(tools) == ["cancel_order", "get_balances", "get_ticker", "list_markets", "list_orders", "me", "place_order"]
    assert set(SPEC["adapter"]["not_offered"]) == {"get_candles"}
    assert "test.deribit.com" in tools["place_order"].description and tools["place_order"].annotations.destructive_hint is True


@pytest.mark.asyncio
@respx.mock
async def test_place_order_routes_side_to_private_buy_or_sell_with_basic_auth():
    # docs.deribit.com trading/private-buy, private-sell: GET /private/<side>?instrument_name&amount&type&price -> result.order
    route = respx.get(url__startswith=f"{BASE}/private/sell").mock(return_value=httpx.Response(200, json={
        "jsonrpc": "2.0", "result": {"trades": [], "order": {"order_id": "ETH-349249", "order_state": "open", "instrument_name": "ETH-PERPETUAL", "direction": "sell",
                                                             "order_type": "limit", "price": 3500.0, "amount": 40.0, "filled_amount": 0.0}}}))
    res = await _server().call_tool("place_order", {"symbol": "ETH-PERPETUAL", "side": "sell", "type": "limit", "quantity": 40, "price": 3500})
    assert res.is_error is False and res.structured_content["order_id"] == "ETH-349249" and res.structured_content["status"] == "open"
    req = route.calls[0].request
    assert dict(req.url.params) == {"instrument_name": "ETH-PERPETUAL", "amount": "40", "type": "limit", "price": "3500"}
    assert req.headers["Authorization"] == "Basic " + base64.b64encode(f"{CREDS['client_id']}:{CREDS['client_secret']}".encode()).decode()
    assert CREDS["client_secret"] not in str(req.url)


@pytest.mark.asyncio
@respx.mock
async def test_side_outside_the_vocabulary_never_builds_a_private_path():
    route = respx.get(url__startswith=f"{BASE}/private/").mock(return_value=httpx.Response(200, json={"jsonrpc": "2.0", "result": {}}))
    res = await _server().call_tool("place_order", {"symbol": "BTC-PERPETUAL", "side": "withdraw", "type": "market", "quantity": 10})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input" and route.call_count == 0


@pytest.mark.asyncio
@respx.mock
async def test_balances_ticker_and_jsonrpc_error_without_secret_leak():
    respx.get(f"{BASE}/private/get_account_summaries").mock(return_value=httpx.Response(200, json={"jsonrpc": "2.0", "result": {"id": 10, "summaries": [
        {"currency": "BTC", "balance": 302.6, "equity": 302.6, "available_funds": 301.4, "margin_balance": 302.6}]}}))
    bal = await _server().call_tool("get_balances", {})
    assert bal.structured_content["balances"][0]["asset"] == "BTC" and bal.structured_content["balances"][0]["available"] == 301.4
    respx.get(url__startswith=f"{BASE}/public/ticker").mock(return_value=httpx.Response(200, json={"jsonrpc": "2.0", "result": {
        "instrument_name": "BTC-PERPETUAL", "last_price": 83548.0, "best_bid_price": 83547.5, "best_ask_price": 83548.0, "mark_price": 83550.1,
        "stats": {"high": 84950.5, "low": 82800.0, "price_change": -1.27, "volume": 19890.0}}}))
    t = await _server().call_tool("get_ticker", {"symbol": "BTC-PERPETUAL"})
    assert (t.structured_content["last"], t.structured_content["bid"], t.structured_content["volume"]) == (83548.0, 83547.5, 19890.0)
    respx.get(url__startswith=f"{BASE}/private/cancel").mock(return_value=httpx.Response(400, json={
        "jsonrpc": "2.0", "error": {"code": 11044, "message": f"not_open_order {CREDS['client_secret']}"}}))
    bad = await _server().call_tool("cancel_order", {"order_id": "ETH-1"})
    assert bad.is_error is True and bad.structured_content["error"] == "upstream_error"
    assert "not_open_order" in bad.content[0].text and CREDS["client_secret"] not in bad.content[0].text
