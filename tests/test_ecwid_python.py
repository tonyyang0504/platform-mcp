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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "ecwid.json").read_text(encoding="utf-8"))


def _server():
    # store_id is a non-secret config field: every path is https://app.ecwid.com/api/v3/{store_id}/...
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"token": "secret_t", "store_id": "12345"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_channel_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["create_listing", "end_listing", "list_orders", "mark_shipped", "me", "set_inventory", "update_listing"]  # listing_metrics not offered
    el = next(t for t in tools if t.name == "end_listing")
    assert el.annotations.destructive_hint is True and el.meta["platform_mcp/endpoint"].endswith("/products/{listing_id}") and SPEC["adapter"]["tools"]["end_listing"]["method"] == "PUT"


@pytest.mark.asyncio
@respx.mock
async def test_create_listing_posts_the_documented_body_to_the_configured_store():
    # docs.ecwid.com/api-reference/rest-api/products/create-product -> {id}
    route = respx.post("https://app.ecwid.com/api/v3/12345/products").mock(return_value=httpx.Response(200, json={"id": 39766764}))
    res = await _server().call_tool("create_listing", {"title": "Blue Mug", "price": 12.5, "sku": "MUG-1", "quantity": 4, "description": "A mug"})
    assert res.is_error is False and res.structured_content["listing_id"] == "39766764" and res.structured_content["status"] == "created"
    req = route.calls.last.request
    assert json.loads(req.content) == {"name": "Blue Mug", "sku": "MUG-1", "price": 12.5, "quantity": 4, "description": "A mug"}
    assert req.headers["Authorization"] == "Bearer secret_t"


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_pages_by_offset_and_maps_the_documented_fields():
    # docs.ecwid.com/api-reference/rest-api/orders/search-orders -> {total, count, offset, limit, items[]}
    respx.get("https://app.ecwid.com/api/v3/12345/orders").mock(return_value=httpx.Response(200, json={
        "total": 41, "count": 1, "offset": 20, "limit": 20,
        "items": [{"id": "XJ12H", "orderNumber": 15, "total": 40.6, "paymentStatus": "PAID", "fulfillmentStatus": "SHIPPED", "createDate": "2024-05-01 05:26:28 +0000", "trackingNumber": "1Z999"}]}))
    res = await _server().call_tool("list_orders", {"status": "SHIPPED", "since": "1447804800", "page": 2, "limit": 20})
    assert res.is_error is False
    o = res.structured_content["orders"][0]
    assert o["id"] == "XJ12H" and o["status"] == "SHIPPED" and o["total"] == 40.6 and o["created_at"].startswith("2024-05-01") and o["tracking_number"] == "1Z999"
    assert res.structured_content["total"] == 41 and res.structured_content["next_page"] is None
    params = respx.calls.last.request.url.params
    assert params["offset"] == "20" and params["limit"] == "20" and params["fulfillmentStatus"] == "SHIPPED" and params["createdFrom"] == "1447804800"


@pytest.mark.asyncio
@respx.mock
async def test_mark_shipped_nests_the_carrier_under_shipping_option():
    # docs.ecwid.com/api-reference/rest-api/orders/update-order -> {updateCount}
    route = respx.put("https://app.ecwid.com/api/v3/12345/orders/XJ12H").mock(return_value=httpx.Response(200, json={"updateCount": 1}))
    res = await _server().call_tool("mark_shipped", {"order_id": "XJ12H", "carrier": "UPS", "tracking_number": "1Z999"})
    assert res.is_error is False and res.structured_content["status"] == "shipped"
    assert json.loads(route.calls.last.request.content) == {"fulfillmentStatus": "SHIPPED", "trackingNumber": "1Z999", "shippingOption": {"shippingCarrierName": "UPS"}}


@pytest.mark.asyncio
@respx.mock
async def test_end_listing_disables_the_product_with_a_json_boolean():
    route = respx.put("https://app.ecwid.com/api/v3/12345/products/39766764").mock(return_value=httpx.Response(200, json={"updateCount": 1}))
    res = await _server().call_tool("end_listing", {"listing_id": "39766764"})
    assert res.is_error is False and res.structured_content["status"] == "disabled"
    assert json.loads(route.calls.last.request.content) == {"enabled": False}
    assert route.calls.last.request.method == "PUT"  # reversible, not DELETE


@pytest.mark.asyncio
@respx.mock
async def test_forbidden_scope_is_an_auth_error_result():
    respx.put("https://app.ecwid.com/api/v3/12345/products/39766764").mock(return_value=httpx.Response(403, json={"errorMessage": "Access denied"}))
    res = await _server().call_tool("end_listing", {"listing_id": "39766764"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 403
