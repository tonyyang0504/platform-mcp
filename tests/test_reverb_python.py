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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "reverb.json").read_text(encoding="utf-8"))
API = "https://api.reverb.com/api"
CREDS = {"token": "774c5112345abcd3f32e662e885e0436", "currency": "USD"}


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test")
    t.fixed_headers = a["headers"]
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
@respx.mock
async def test_me_sends_hal_and_version_headers():
    route = respx.get(f"{API}/my/account").mock(return_value=httpx.Response(200, json={"shop": {"name": "Guitar Shop"}}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["end_listing", "list_orders", "mark_shipped", "me", "set_inventory", "update_listing"]
    assert (await server.call_tool("me", {})).is_error is False
    h = route.calls.last.request.headers
    assert h["Authorization"] == "Bearer 774c5112345abcd3f32e662e885e0436" and h["Accept"] == "application/hal+json" and h["Accept-Version"] == "3.0"


@pytest.mark.asyncio
@respx.mock
async def test_listing_writes():
    put = respx.put(f"{API}/listings/123").mock(return_value=httpx.Response(200, json={"listing": {"id": 123}}))
    await _server().call_tool("update_listing", {"listing_id": "123", "price": 5000, "title": "Strat"})
    req = put.calls.last.request
    assert req.headers["Content-Type"] == "application/hal+json"
    assert json.loads(req.content) == {"title": "Strat", "price": {"amount": "5000", "currency": "USD"}}
    await _server().call_tool("set_inventory", {"listing_id": "123", "quantity": 5})
    assert json.loads(put.calls.last.request.content) == {"has_inventory": True, "inventory": 5}
    end = respx.put(f"{API}/my/listings/123/state/end").mock(return_value=httpx.Response(200, json={}))
    res = await _server().call_tool("end_listing", {"listing_id": "123"})
    assert res.structured_content["status"] == "ended" and json.loads(end.calls.last.request.content) == {"reason": "not_sold"}


@pytest.mark.asyncio
@respx.mock
async def test_orders_default_all_bucket_and_ship():
    route = respx.get(f"{API}/my/orders/selling/all").mock(return_value=httpx.Response(200, json={"total": 2, "current_page": 1, "total_pages": 1, "orders": [
        {"order_number": "2", "status": "paid", "total": {"amount": "103.00", "currency": "USD"}, "created_at": "2026-09-20T18:38:29-05:00"}]}))
    res = await _server().call_tool("list_orders", {"since": "2026-09-01T00:00-00:00"})
    o = res.structured_content["orders"][0]
    assert o["id"] == "2" and o["total"] == "103.00" and res.structured_content["total"] == 2
    assert route.calls.last.request.url.params["updated_start_date"] == "2026-09-01T00:00-00:00"
    respx.get(f"{API}/my/orders/selling/awaiting_shipment").mock(return_value=httpx.Response(200, json={"total": 0, "orders": []}))
    assert (await _server().call_tool("list_orders", {"status": "awaiting_shipment"})).is_error is False
    ship = respx.post(f"{API}/my/orders/selling/2/ship").mock(return_value=httpx.Response(200, json={}))
    await _server().call_tool("mark_shipped", {"order_id": "2", "carrier": "USPS", "tracking_number": "12345678"})
    assert json.loads(ship.calls.last.request.content) == {"provider": "USPS", "tracking_number": "12345678", "send_notification": True}
