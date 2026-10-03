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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "flipkart.json").read_text(encoding="utf-8"))
URL = "https://api.flipkart.net/sellers/v3/shipments/filter/"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {"access_token": "FK-token-f638949a"}, 50, "test"))


@pytest.mark.asyncio
@respx.mock
async def test_me_probe_filters_one_shipment():
    route = respx.post(URL).mock(return_value=httpx.Response(200, json={"hasMore": False, "shipments": []}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["list_orders", "me"]
    assert (await server.call_tool("me", {})).is_error is False
    req = route.calls.last.request
    assert req.headers["Authorization"] == "Bearer FK-token-f638949a"
    assert json.loads(req.content) == {"filter": {"type": "preDispatch", "states": ["APPROVED"]}, "pagination": {"pageSize": 1}}


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_derives_filter_type_from_status():
    route = respx.post(URL).mock(return_value=httpx.Response(200, json={"hasMore": False, "shipments": [
        {"shipmentId": "S1", "orderItems": [{"orderId": "OD1234", "status": "SHIPPED", "orderDate": "2026-09-20T10:00:00+05:30", "priceComponents": {"totalPrice": 499.0}}]}]}))
    res = await _server().call_tool("list_orders", {"status": "SHIPPED", "since": "2026-09-01T00:00:00+05:30", "limit": 10})
    o = res.structured_content["orders"][0]
    assert o["id"] == "OD1234" and o["total"] == 499.0 and o["currency"] == "INR"
    assert json.loads(route.calls.last.request.content) == {"filter": {"type": "postDispatch", "states": ["SHIPPED"], "orderDate": {"from": "2026-09-01T00:00:00+05:30"}}, "pagination": {"pageSize": 10}}
    res = await _server().call_tool("list_orders", {"status": "CANCELLED"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input"


@pytest.mark.asyncio
@respx.mock
async def test_expired_token_is_auth_error():
    respx.post(URL).mock(return_value=httpx.Response(401, json={"error": "invalid_token"}))
    res = await _server().call_tool("list_orders", {"status": "APPROVED"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
