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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "faire.json").read_text(encoding="utf-8"))
API = "https://www.faire.com/external-api/v2"
CREDS = {"access_token": "oat_4f9c2d7e81b3", "app_credentials": "YXBhXzEyMzpzZWNyZXQ="}


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test")
    t.fixed_headers = a["headers"]
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
@respx.mock
async def test_me_sends_both_oauth_headers():
    route = respx.get(f"{API}/brands/profile").mock(return_value=httpx.Response(200, json={"brand_id": "b_60ae65c4", "name": "Toques", "currency": "USD"}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["end_listing", "list_orders", "mark_shipped", "me", "set_inventory", "update_listing"]
    res = await server.call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["brand_id"] == "b_60ae65c4"
    h = route.calls.last.request.headers
    assert h["X-FAIRE-OAUTH-ACCESS-TOKEN"] == "oat_4f9c2d7e81b3" and h["X-FAIRE-APP-CREDENTIALS"] == "YXBhXzEyMzpzZWNyZXQ="


@pytest.mark.asyncio
@respx.mock
async def test_orders_cursor_and_since():
    route = respx.get(f"{API}/orders").mock(return_value=httpx.Response(200, json={"orders": [
        {"id": "bo_bxdmjbwxid", "state": "NEW", "created_at": "2026-09-20T00:09:15.000Z", "shipments": []}], "limit": 25, "cursor": "c_next"}))
    res = await _server().call_tool("list_orders", {"since": "2026-09-01T00:00:00.000Z", "cursor": "c_1"})
    out = res.structured_content
    assert out["orders"][0]["id"] == "bo_bxdmjbwxid" and out["orders"][0]["status"] == "NEW" and out["next_cursor"] == "c_next"
    p = route.calls.last.request.url.params
    assert p["updated_at_min"] == "2026-09-01T00:00:00.000Z" and p["cursor"] == "c_1" and p["limit"] == "25" and "page" not in p


@pytest.mark.asyncio
@respx.mock
async def test_inventory_by_sku_and_ship():
    inv = respx.patch(f"{API}/product-inventory/by-skus").mock(return_value=httpx.Response(200, json={"inventories": {}, "bulk_validation_errors": {}}))
    res = await _server().call_tool("set_inventory", {"sku": "vanilla-2019", "quantity": 7})
    assert res.structured_content["status"] == "updated"
    assert json.loads(inv.calls.last.request.content) == {"inventories": [{"sku": "vanilla-2019", "on_hand_quantity": 7}]}
    ship = respx.post(f"{API}/orders/bo_x1/shipments").mock(return_value=httpx.Response(200, json={}))
    await _server().call_tool("mark_shipped", {"order_id": "bo_x1", "carrier": "UPS", "tracking_number": "1Z999"})
    assert json.loads(ship.calls.last.request.content) == {"shipments": [{"order_id": "bo_x1", "carrier": "UPS", "tracking_code": "1Z999", "shipping_type": "SHIP_ON_YOUR_OWN"}]}


@pytest.mark.asyncio
@respx.mock
async def test_product_patch_and_delete():
    patch = respx.patch(f"{API}/products/p_123").mock(return_value=httpx.Response(200, json={"id": "p_123"}))
    await _server().call_tool("update_listing", {"listing_id": "p_123", "title": "Candle", "price": 12})
    assert json.loads(patch.calls.last.request.content) == {"name": "Candle"}
    respx.delete(f"{API}/products/p_123").mock(return_value=httpx.Response(200, json={}))
    assert (await _server().call_tool("end_listing", {"listing_id": "p_123"})).structured_content["status"] == "deleted"
    respx.get(f"{API}/brands/profile").mock(return_value=httpx.Response(401, json={"message": "bad token oat_4f9c2d7e81b3"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and "oat_4f9c2d7e81b3" not in json.dumps(res.structured_content or {}) + str(res.content)
