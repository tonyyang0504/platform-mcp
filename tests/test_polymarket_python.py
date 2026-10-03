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

SPEC = json.loads((ROOT / "catalog" / "trading" / "polymarket.json").read_text(encoding="utf-8"))
GAMMA = "https://gamma-api.polymarket.com"


def _server():
    return build_server(SPEC, transport=Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test"))


@pytest.mark.asyncio
async def test_public_reads_only_and_writes_explained():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_ticker", "list_markets", "me"]
    no = SPEC["adapter"]["not_offered"]
    assert set(no) == {"get_candles", "get_balances", "list_orders", "place_order", "cancel_order"} and "EIP-712" in no["place_order"]


@pytest.mark.asyncio
@respx.mock
async def test_list_markets_pages_with_limit_and_offset():
    route = respx.get(url__startswith=f"{GAMMA}/markets").mock(return_value=httpx.Response(200, json=[
        {"id": "4464920", "question": "Will Norway win on 2026-09-24?", "conditionId": "0x80c7", "slug": "unl-nor-den-2026-09-24-nor",
         "outcomes": "[\"Yes\", \"No\"]", "outcomePrices": "[\"0.575\", \"0.425\"]", "volume": "870799.05", "active": True, "closed": False}]))
    res = await _server().call_tool("list_markets", {"page": 3, "limit": 10})
    assert res.is_error is False
    m = res.structured_content["markets"][0]
    assert m["symbol"] == "unl-nor-den-2026-09-24-nor" and m["market_id"] == "4464920" and res.structured_content["next_page"] is None
    p = route.calls[0].request.url.params
    assert (p["limit"], p["offset"], p["closed"], p["active"]) == ("10", "20", "false", "true")


@pytest.mark.asyncio
@respx.mock
async def test_ticker_by_slug_and_unknown_slug():
    respx.get(f"{GAMMA}/markets/slug/unl-nor-den-2026-09-24-nor").mock(return_value=httpx.Response(200, json={
        "slug": "unl-nor-den-2026-09-24-nor", "question": "Will Norway win?", "bestBid": 0.57, "bestAsk": 0.58, "lastTradePrice": 0.58, "volume24hr": 991170.7}))
    t = await _server().call_tool("get_ticker", {"symbol": "unl-nor-den-2026-09-24-nor"})
    assert (t.structured_content["bid"], t.structured_content["ask"], t.structured_content["last"]) == (0.57, 0.58, 0.58)
    respx.get(f"{GAMMA}/markets/slug/nope").mock(return_value=httpx.Response(404, json={"type": "not found error", "error": "id not found"}))
    bad = await _server().call_tool("get_ticker", {"symbol": "nope"})
    assert bad.is_error is True and bad.structured_content["error"] == "not_found"
