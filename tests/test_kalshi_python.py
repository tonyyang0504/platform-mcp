"""Kalshi public market data (forge stress test 2026-10, OpenAPI YAML): cursor pagination, fixed filters."""
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

SPEC = json.loads((ROOT / "catalog" / "trading" / "kalshi.json").read_text(encoding="utf-8"))
BASE = "https://api.elections.kalshi.com/trade-api/v2"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_markets_cursor():
    route = respx.get(f"{BASE}/markets").mock(side_effect=[
        httpx.Response(200, json={"cursor": "abc", "markets": [{"ticker": "KXA-1", "event_ticker": "KXA", "market_type": "binary"}]}),
        httpx.Response(200, json={"cursor": "", "markets": [{"ticker": "KXB-1", "event_ticker": "KXB", "market_type": "binary"}]})])
    p1 = (await _server().call_tool("list_markets", {"limit": 1})).structured_content
    assert p1["markets"][0]["symbol"] == "KXA-1" and p1["next_cursor"] == "abc" and p1["next_page"] is None
    q = route.calls.last.request.url.params
    assert (q["limit"], q["status"], q["mve_filter"]) == ("1", "open", "exclude") and "cursor" not in q
    p2 = (await _server().call_tool("list_markets", {"limit": 1, "cursor": "abc"})).structured_content
    assert p2["markets"][0]["symbol"] == "KXB-1" and p2["next_cursor"] is None
    assert route.calls.last.request.url.params["cursor"] == "abc"


@pytest.mark.asyncio
@respx.mock
async def test_ticker_and_unknown():
    respx.get(f"{BASE}/markets/KXA-1").mock(return_value=httpx.Response(200, json={"market": {"ticker": "KXA-1", "last_price_dollars": "0.4200", "yes_bid_dollars": "0.4100", "yes_ask_dollars": "0.4300", "volume_24h_fp": "12.00"}}))
    respx.get(f"{BASE}/markets/NOPE").mock(return_value=httpx.Response(404, json={"error": {"code": "not_found", "message": "not found"}}))
    t = (await _server().call_tool("get_ticker", {"symbol": "KXA-1"})).structured_content
    assert (t["last"], t["bid"], t["ask"], t["volume"]) == (0.42, 0.41, 0.43, 12)
    r = await _server().call_tool("get_ticker", {"symbol": "NOPE"})
    assert r.is_error and r.structured_content["error"] == "not_found"
