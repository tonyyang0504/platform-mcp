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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "blurb.json").read_text(encoding="utf-8"))


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": "key-1", "shared_secret": "secret-1"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["create_order", "get_order", "me"]
    co = next(t for t in tools if t.name == "create_order")
    assert co.annotations.read_only_hint is False and co.annotations.destructive_hint is True
    assert co.meta["platform_mcp/endpoint"] == "/orders/create" and co.meta["platform_mcp/docs"] == "https://docs.api.rpiprint.com/api-reference"
    assert set(SPEC["adapter"]["not_offered"]) == {"list_products", "get_product", "quote_shipping", "track"}


@pytest.mark.asyncio
@respx.mock
async def test_me_lists_orders_with_http_basic_key_and_secret():
    # docs.api.rpiprint.com/api-reference: GET /orders?limit=10 -> {totalCount, offset, limit, nextOffset, orders[]}
    respx.get("https://open.api.rpiprint.com/orders").mock(return_value=httpx.Response(200, json={"totalCount": 0, "offset": 0, "limit": 10, "nextOffset": None, "prevOffset": None, "orders": []}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["ok"] is True and res.structured_content["account"]["totalCount"] == 0
    req = respx.calls.last.request
    assert req.url.params["limit"] == "10"
    assert req.headers["Authorization"] == "Basic " + base64.b64encode(b"key-1:secret-1").decode()


@pytest.mark.asyncio
@respx.mock
async def test_create_order_sends_the_documented_body_in_usd():
    route = respx.post("https://open.api.rpiprint.com/orders/create").mock(return_value=httpx.Response(201, json={"customerOrderId": "ORD-77", "statusCode": 201, "statusDescription": "Order received"}))
    res = await _server().call_tool("create_order", {
        "items": [{"sku": "HC_8x10_LAND", "quantity": 1, "retailPrice": "29.99", "itemDescription": "Photo book", "product": {"coverUrl": "https://example.com/c.pdf", "gutsUrl": "https://example.com/g.pdf"}}],
        "shipping_address": {"name": "J Smith", "address1": "1 St", "city": "Seattle", "postal": "98101", "country": "US", "regionCode": "WA"},
        "shipping_option": "standard"})
    assert res.is_error is False
    assert res.structured_content["id"] == "ORD-77" and res.structured_content["status"] == "Order received"
    body = json.loads(route.calls.last.request.content)
    assert body["currency"] == "USD" and body["shippingClassification"] == "standard"
    assert body["destination"]["regionCode"] == "WA" and body["orderItems"][0]["sku"] == "HC_8x10_LAND"
    assert set(body) == {"currency", "destination", "orderItems", "shippingClassification"}


@pytest.mark.asyncio
@respx.mock
async def test_get_order_reads_nested_status_pricing_and_tracking():
    respx.get("https://open.api.rpiprint.com/orders/ORD-77").mock(return_value=httpx.Response(200, json={
        "order": {"customerOrderId": "ORD-77", "currency": "USD", "status": "SHIPPED", "shippingClassification": "standard"},
        "pricing": {"orderTotal": 41.2, "itemsTotal": 29.99, "taxesTotal": 3.21, "shippingTotal": 8.0, "currency": "USD"},
        "shipmentTracking": [{"shipmentId": "s1", "trackingNumber": "9400111", "shipMethod": "USPS", "shipDate": "2026-09-20"}],
        "paymentInfo": {"total": 41.2, "paymentStatus": "CHARGED"}}))
    res = await _server().call_tool("get_order", {"id": "ORD-77"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["id"] == "ORD-77" and sc["status"] == "SHIPPED" and sc["total"] == 41.2 and sc["currency"] == "USD" and sc["tracking_number"] == "9400111"


@pytest.mark.asyncio
@respx.mock
async def test_bad_credentials_are_an_auth_error_result():
    respx.get("https://open.api.rpiprint.com/orders/ORD-1").mock(return_value=httpx.Response(401, text="Unauthorized"))
    res = await _server().call_tool("get_order", {"id": "ORD-1"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
