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

SPEC = json.loads((ROOT / "catalog" / "market_data" / "deribit_collector.json").read_text(encoding="utf-8"))
BASE = "https://www.deribit.com/api/v2"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_public_read_verbs_only():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["me", "search_symbols"]
    assert all(t.annotations.read_only_hint is True for t in tools)
    assert "parallel arrays" in SPEC["adapter"]["not_offered"]["get_candles"]


@pytest.mark.asyncio
@respx.mock
async def test_search_symbols_lists_instruments_of_a_currency():
    # docs.deribit.com api-reference/market-data/public-get_instruments example excerpt
    respx.get(f"{BASE}/public/get_instruments").mock(return_value=httpx.Response(200, json={
        "jsonrpc": "2.0", "id": 1, "result": [
            {"instrument_name": "BTC-PERPETUAL", "instrument_id": 124972, "kind": "future", "base_currency": "BTC", "quote_currency": "USD", "counter_currency": "USD",
             "is_active": True, "tick_size": 0.5, "contract_size": 10, "settlement_currency": "BTC", "settlement_period": "perpetual", "price_index": "btc_usd", "expiration_timestamp": 32503708800000}]}))
    res = await _server().call_tool("search_symbols", {"query": "BTC"})
    assert res.is_error is False
    r = res.structured_content["results"][0]
    assert r["symbol"] == "BTC-PERPETUAL" and r["type"] == "future" and r["name"] == "btc_usd" and r["raw"]["is_active"] is True
    assert respx.calls.last.request.url.params["currency"] == "BTC"


@pytest.mark.asyncio
@respx.mock
async def test_me_probes_public_test():
    respx.get(f"{BASE}/public/test").mock(return_value=httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {"version": "2.1.26"}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["ok"] is True and res.structured_content["account"]["result"]["version"] == "2.1.26"


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_is_error_result():
    respx.get(f"{BASE}/public/get_instruments").mock(return_value=httpx.Response(429, json={"jsonrpc": "2.0", "error": {"code": 10028, "message": "too_many_requests"}}))
    res = await _server().call_tool("search_symbols", {"query": "ETH"})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited"
