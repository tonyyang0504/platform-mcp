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

SPEC = json.loads((ROOT / "catalog" / "trading" / "useq.json").read_text(encoding="utf-8"))
CREDS = {"api_key": "PKTESTKEY123456", "api_secret": "SECRET-alpaca-abcdef"}
PAPER = "https://paper-api.alpaca.markets"


def _server():
    return build_server(SPEC, transport=Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], dict(CREDS), 50, "test"))


@pytest.mark.asyncio
async def test_paper_host_by_default_and_verbs():
    tools = {t.name: t for t in await _server().list_tools()}
    assert sorted(tools) == ["cancel_order", "get_balances", "get_ticker", "list_markets", "list_orders", "me", "place_order"]
    assert SPEC["adapter"]["base_url"] == PAPER and set(SPEC["adapter"]["not_offered"]) == {"get_candles"}
    assert "REAL ORDER WITH REAL FUNDS" in tools["place_order"].description and tools["cancel_order"].annotations.destructive_hint is True


@pytest.mark.asyncio
@respx.mock
async def test_place_order_body_and_key_headers():
    # docs.alpaca.markets postorder: POST /v2/orders {symbol, qty, side, type, time_in_force, limit_price}
    route = respx.post(f"{PAPER}/v2/orders").mock(return_value=httpx.Response(200, json={
        "id": "61e69015-8549-4bfd-b9c3-01e75843f47d", "client_order_id": "eb9e2aaa", "symbol": "AAPL", "qty": "3", "side": "buy", "type": "limit",
        "limit_price": "180.5", "status": "accepted", "time_in_force": "day"}))
    res = await _server().call_tool("place_order", {"symbol": "AAPL", "side": "buy", "type": "limit", "quantity": 3, "price": 180.5})
    assert res.is_error is False and res.structured_content["order_id"] == "61e69015-8549-4bfd-b9c3-01e75843f47d" and res.structured_content["status"] == "accepted"
    req = route.calls[0].request
    assert json.loads(req.content) == {"symbol": "AAPL", "qty": "3", "side": "buy", "type": "limit", "time_in_force": "day", "limit_price": "180.5"}
    assert req.headers["APCA-API-KEY-ID"] == CREDS["api_key"] and req.headers["APCA-API-SECRET-KEY"] == CREDS["api_secret"]


@pytest.mark.asyncio
@respx.mock
async def test_cancel_204_and_snapshot_on_the_data_host():
    respx.delete(f"{PAPER}/v2/orders/61e69015").mock(return_value=httpx.Response(204))
    res = await _server().call_tool("cancel_order", {"order_id": "61e69015"})
    assert res.is_error is False and res.structured_content["status"] == "cancel_requested"
    snap = respx.get("https://data.alpaca.markets/v2/stocks/AAPL/snapshot").mock(return_value=httpx.Response(200, json={
        "symbol": "AAPL", "latestTrade": {"p": 181.02, "s": 100}, "latestQuote": {"bp": 181.0, "ap": 181.05}, "dailyBar": {"o": 179.1, "h": 182.0, "l": 178.9, "c": 181.02, "v": 51234567},
        "prevDailyBar": {"c": 178.5}}))
    t = await _server().call_tool("get_ticker", {"symbol": "AAPL"})
    assert (t.structured_content["last"], t.structured_content["bid"], t.structured_content["ask"], t.structured_content["volume"]) == (181.02, 181.0, 181.05, 51234567)
    assert snap.calls[0].request.headers["APCA-API-KEY-ID"] == CREDS["api_key"]


@pytest.mark.asyncio
@respx.mock
async def test_rejection_is_an_error_without_secret_leak():
    respx.post(f"{PAPER}/v2/orders").mock(return_value=httpx.Response(422, json={"code": 40010001, "message": f"qty must be > 0 ({CREDS['api_secret']})"}))
    res = await _server().call_tool("place_order", {"symbol": "AAPL", "side": "sell", "type": "market", "quantity": 0})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input"
    assert "qty must be" in res.content[0].text and CREDS["api_secret"] not in res.content[0].text
