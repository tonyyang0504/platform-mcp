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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "squarespace.json").read_text(encoding="utf-8"))


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": "k"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_the_expressible_verbs_are_tools():
    tools = await _server().list_tools()
    # products/fulfillments/inventory bodies are arrays of objects or {present, value} wrappers -> not offered
    assert sorted(t.name for t in tools) == ["end_listing", "list_orders", "me"]
    assert set(SPEC["adapter"]["not_offered"]) == {"create_listing", "update_listing", "set_inventory", "mark_shipped", "listing_metrics"}


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_maps_the_documented_order_and_does_not_send_page_params():
    # developers.squarespace.com/commerce-apis/retrieve-all-orders -> {result: [Order], pagination}
    respx.get("https://api.squarespace.com/1.0/commerce/orders").mock(return_value=httpx.Response(200, json={
        "result": [{"id": "585d498fdee9f31a60284a37", "orderNumber": "3", "createdOn": "2016-12-23T15:58:07.187Z", "modifiedOn": "2016-12-23T15:58:07.187Z",
                    "fulfillmentStatus": "PENDING", "grandTotal": {"value": "49.99", "currency": "USD"}, "fulfillments": [{"trackingNumber": "103932814692659", "carrierName": "FedEx"}]}],
        "pagination": {"hasNextPage": False, "nextPageCursor": None}}))
    res = await _server().call_tool("list_orders", {"status": "PENDING"})
    assert res.is_error is False
    o = res.structured_content["orders"][0]
    assert o["id"] == "585d498fdee9f31a60284a37" and o["status"] == "PENDING" and o["total"] == "49.99" and o["currency"] == "USD" and o["tracking_number"] == "103932814692659"
    assert res.structured_content["next_page"] is None
    req = respx.calls.last.request
    assert req.url.params["fulfillmentStatus"] == "PENDING" and "page" not in req.url.params and "cursor" not in req.url.params
    assert req.headers["Authorization"] == "Bearer k" and req.headers["User-Agent"] == "test"


@pytest.mark.asyncio
@respx.mock
async def test_invalid_key_is_an_auth_error_result():
    respx.get("https://api.squarespace.com/v2/commerce/products").mock(return_value=httpx.Response(401, json={"type": "INVALID_AUTHENTICATION", "message": "Invalid credentials"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 401


@pytest.mark.asyncio
@respx.mock
async def test_end_listing_sends_the_documented_change_wrapper_with_json_booleans():
    # developers.squarespace.com/commerce-apis/update-product -> {isVisible: {present, value}} and the updated ProductV2
    route = respx.post("https://api.squarespace.com/v2/commerce/products/5c4f1b2e3a9f8b0012345678").mock(return_value=httpx.Response(200, json={
        "id": "5c4f1b2e3a9f8b0012345678", "type": "PHYSICAL", "storePageId": "5c4f1b2e3a9f8b0012000000", "name": "Blue Mug", "isVisible": False,
        "createdOn": "2024-08-25T15:00:00Z", "modifiedOn": "2024-08-26T15:00:00Z", "url": "https://example.squarespace.com/shop/p/blue-mug"}))
    res = await _server().call_tool("end_listing", {"listing_id": "5c4f1b2e3a9f8b0012345678"})
    assert res.is_error is False and res.structured_content["status"] == "hidden" and res.structured_content["raw"]["isVisible"] is False
    assert json.loads(route.calls.last.request.content) == {"isVisible": {"present": True, "value": False}}
