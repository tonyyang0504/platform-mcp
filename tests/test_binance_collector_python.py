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

SPEC = json.loads((ROOT / "catalog" / "market_data" / "binance_collector.json").read_text(encoding="utf-8"))
BASE = "https://api.binance.com"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_public_read_verbs_only():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_candles", "me", "search_symbols"]
    assert all(t.annotations.read_only_hint is True for t in tools)
    assert SPEC["adapter"]["base_url"] == BASE and SPEC["adapter"]["auth"]["type"] == "none"


@pytest.mark.asyncio
@respx.mock
async def test_get_candles_caps_limit_and_maps_rows():
    rows = [[1499040000000 + i * 3600000, "1", "2", "0.5", "1.5", "10", 0, "0", 0, "0", "0", "0"] for i in range(3)]
    respx.get(f"{BASE}/api/v3/klines").mock(return_value=httpx.Response(200, json=rows))
    res = await _server().call_tool("get_candles", {"symbol": "ETHUSDT", "interval": "1h", "limit": 5000})
    assert res.is_error is False
    cs = res.structured_content["candles"]
    assert len(cs) == 3 and cs[2]["time"] == str(1499040000000 + 2 * 3600000) and cs[0]["close"] == 1.5
    assert respx.calls.last.request.url.params["limit"] == "1000"  # Binance max


@pytest.mark.asyncio
@respx.mock
async def test_weight_ban_429_is_a_rate_limited_result():
    respx.get(f"{BASE}/api/v3/ping").mock(return_value=httpx.Response(429, headers={"Retry-After": "10"}, json={"code": -1003, "msg": "Too many requests."}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 10
