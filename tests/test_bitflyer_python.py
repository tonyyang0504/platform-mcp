"""bitFlyer Lightning public API (forge stress test 2026-10, Japanese docs)."""
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

SPEC = json.loads((ROOT / "catalog" / "trading" / "bitflyer.json").read_text(encoding="utf-8"))
BASE = "https://api.bitflyer.com"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_markets_and_ticker():
    respx.get(f"{BASE}/v1/getmarkets").mock(return_value=httpx.Response(200, json=[{"product_code": "ETH_JPY", "market_type": "Spot"}, {"product_code": "BTC_JPY", "market_type": "Spot"}, {"product_code": "FX_BTC_JPY", "market_type": "FX"}]))
    route = respx.get(f"{BASE}/v1/getticker").mock(return_value=httpx.Response(200, json={"product_code": "BTC_JPY", "best_bid": 13264727.0, "best_ask": 13270396.0, "ltp": 13265634.0, "volume": 1536.3, "volume_by_product": 436.6}))
    m = (await _server().call_tool("list_markets", {"query": "btc"})).structured_content
    assert [x["symbol"] for x in m["markets"]] == ["BTC_JPY", "FX_BTC_JPY"] and m["markets"][1]["type"] == "FX"
    t = (await _server().call_tool("get_ticker", {"symbol": "BTC_JPY"})).structured_content
    assert (t["last"], t["bid"], t["ask"], t["volume"]) == (13265634.0, 13264727.0, 13270396.0, 436.6)
    assert route.calls.last.request.url.params["product_code"] == "BTC_JPY"


@pytest.mark.asyncio
@respx.mock
async def test_invalid_product():
    respx.get(f"{BASE}/v1/getticker").mock(return_value=httpx.Response(400, json={"status": -100, "error_message": "Invalid product", "data": None}))
    r = await _server().call_tool("get_ticker", {"symbol": "NOPE"})
    assert r.is_error and r.structured_content["error"] == "invalid_input"
