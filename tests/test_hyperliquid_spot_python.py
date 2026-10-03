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

SPEC = json.loads((ROOT / "catalog" / "trading" / "hyperliquid_spot.json").read_text(encoding="utf-8"))
WALLET = "0x2222222222222222222222222222222222222222"
INFO = "https://api.hyperliquid.xyz/info"


def _server(creds=None):
    return build_server(SPEC, transport=Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], creds or {}, 50, "test"))


@pytest.mark.asyncio
async def test_read_verbs_only_writes_need_a_wallet_signature():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_balances", "get_ticker", "list_markets", "list_orders", "me"]
    assert all(t.annotations.read_only_hint is True for t in tools)
    assert set(SPEC["adapter"]["not_offered"]) == {"get_candles", "place_order", "cancel_order"}
    assert "EIP-712" in SPEC["adapter"]["not_offered"]["place_order"] and SPEC["adapter"]["auth"]["fields"] == []


@pytest.mark.asyncio
@respx.mock
async def test_list_markets_posts_spot_meta():
    # info-endpoint/spot: {"type": "spotMeta"} -> {tokens: [...], universe: [{name, tokens, index, isCanonical}]}
    route = respx.post(INFO).mock(return_value=httpx.Response(200, json={
        "tokens": [{"name": "USDC", "szDecimals": 8, "weiDecimals": 8, "index": 0, "tokenId": "0x6d1e", "isCanonical": True}],
        "universe": [{"name": "PURR/USDC", "tokens": [1, 0], "index": 0, "isCanonical": True}, {"name": "@1", "tokens": [2, 0], "index": 1, "isCanonical": False}]}))
    res = await _server().call_tool("list_markets", {})
    assert [m["symbol"] for m in res.structured_content["markets"]] == ["PURR/USDC", "@1"]
    assert json.loads(route.calls.last.request.content) == {"type": "spotMeta"}


@pytest.mark.asyncio
@respx.mock
async def test_balances_use_the_configured_address_and_ticker_reads_the_book():
    route = respx.post(INFO).mock(side_effect=[
        httpx.Response(200, json={"balances": [{"coin": "USDC", "token": 0, "hold": "0.0", "total": "14.625485", "entryNtl": "0.0"},
                                               {"coin": "PURR", "token": 1, "hold": "0", "total": "2000", "entryNtl": "1234.56"}]}),
        httpx.Response(200, json={"coin": "PURR/USDC", "time": 1, "levels": [[{"px": "0.21", "sz": "100", "n": 1}], [{"px": "0.22", "sz": "50", "n": 2}]]})])
    server = _server({"wallet_address": WALLET})
    bal = await server.call_tool("get_balances", {})
    assert [(b["asset"], b["total"]) for b in bal.structured_content["balances"]] == [("USDC", "14.625485"), ("PURR", "2000")]
    assert json.loads(route.calls[0].request.content) == {"type": "spotClearinghouseState", "user": WALLET}
    t = await server.call_tool("get_ticker", {"symbol": "PURR/USDC"})
    assert t.structured_content["bid"] == 0.21 and t.structured_content["ask"] == 0.22
    assert json.loads(route.calls[1].request.content) == {"type": "l2Book", "coin": "PURR/USDC"}


@pytest.mark.asyncio
@respx.mock
async def test_upstream_rejection_is_an_is_error_result():
    respx.post(INFO).mock(return_value=httpx.Response(422, text="Failed to deserialize the JSON body into the target type"))
    res = await _server().call_tool("list_orders", {})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input"
