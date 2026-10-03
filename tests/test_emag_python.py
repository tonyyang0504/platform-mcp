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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "emag.json").read_text(encoding="utf-8"))
API = "https://marketplace-api.emag.ro/api-3"
CREDS = {"username": "api-user@shop.ro", "password": "PASSWORDsecret1", "api_host": "marketplace-api.emag.ro"}


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a["envelope"])
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
@respx.mock
async def test_me_uses_basic_auth_on_the_configured_host():
    route = respx.post(f"{API}/vat/read").mock(return_value=httpx.Response(200, json={"isError": False, "messages": [], "results": [{"vat_id": 1, "vat_rate": 0.19}]}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["end_listing", "list_orders", "me", "set_inventory", "update_listing"]
    res = await server.call_tool("me", {})
    assert res.is_error is False
    assert route.calls.last.request.headers["Authorization"] == "Basic " + base64.b64encode(b"api-user@shop.ro:PASSWORDsecret1").decode()


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_sends_top_level_filters():
    route = respx.post(f"{API}/order/read").mock(return_value=httpx.Response(200, json={"isError": False, "messages": [], "results": [
        {"id": 5001, "status": 1, "date": "2026-09-20 10:00:00", "products": [{"id": 1, "sale_price": "99.0000", "currency": "RON", "quantity": 1}]}]}))
    res = await _server().call_tool("list_orders", {"status": "1", "since": "2026-09-01 00:00:00", "limit": 10})
    assert res.is_error is False
    o = res.structured_content["orders"][0]
    assert o["id"] == "5001" and o["status"] == 1 and o["created_at"] == "2026-09-20 10:00:00" and o["currency"] == "RON"
    assert json.loads(route.calls.last.request.content) == {"status": 1, "createdAfter": "2026-09-01 00:00:00", "currentPage": 1, "itemsPerPage": 10}


@pytest.mark.asyncio
@respx.mock
async def test_offer_writes_build_documented_bodies():
    save = respx.post(f"{API}/offer/save").mock(return_value=httpx.Response(200, json={"isError": False, "messages": [], "results": []}))
    res = await _server().call_tool("update_listing", {"listing_id": "243409", "price": 45.5})
    assert res.is_error is False and json.loads(save.calls.last.request.content) == {"data": [{"id": 243409, "sale_price": 45.5}]}
    res = await _server().call_tool("end_listing", {"listing_id": "243409"})
    assert json.loads(save.calls.last.request.content) == {"data": [{"id": 243409, "status": 0}]}
    stock = respx.patch(f"{API}/offer_stock/243409").mock(return_value=httpx.Response(200, json={"isError": False, "messages": [], "results": []}))
    res = await _server().call_tool("set_inventory", {"listing_id": "243409", "quantity": 7})
    assert res.is_error is False and json.loads(stock.calls.last.request.content) == {"data": {"stock": [{"warehouse_id": 1, "value": 7}]}}


@pytest.mark.asyncio
@respx.mock
async def test_is_error_true_is_reported():
    respx.post(f"{API}/offer/save").mock(return_value=httpx.Response(200, json={"isError": True, "messages": ["Invalid offer id"], "results": []}))
    res = await _server().call_tool("end_listing", {"listing_id": "1"})
    assert res.is_error is True and "Invalid offer id" in res.structured_content["message"]
