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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "bigcommerce.json").read_text(encoding="utf-8"))


def _server():
    # store_hash is a non-secret config field in every path: https://api.bigcommerce.com/stores/{store_hash}/...
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"access_token": "tok", "store_hash": "abc123"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_channel_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["create_listing", "end_listing", "list_orders", "mark_shipped", "me", "set_inventory", "update_listing"]  # listing_metrics not offered
    si = next(t for t in tools if t.name == "set_inventory")
    assert si.annotations.read_only_hint is False and si.input_schema["required"] == ["quantity"]
    assert si.meta["platform_mcp/docs"].endswith("/catalog/products/update-product")


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_uses_the_store_hash_and_the_x_auth_token_header():
    # docs.bigcommerce.com .../management/orders/get-orders -> array of orders (V2)
    respx.get("https://api.bigcommerce.com/stores/abc123/v2/orders").mock(return_value=httpx.Response(200, json=[
        {"id": 100, "customer_id": 11, "date_created": "Wed, 13 Mar 2019 16:35:37 +0000", "status_id": 11, "status": "Awaiting Fulfillment",
         "subtotal_inc_tax": "70.0000", "total_inc_tax": "80.0000", "currency_code": "USD", "default_currency_code": "USD", "items_total": 1}]))
    res = await _server().call_tool("list_orders", {"status": "11", "since": "2019-03-01T00:00:00.000-04:00", "limit": 50})
    assert res.is_error is False
    o = res.structured_content["orders"][0]
    assert o["id"] == "100" and o["status"] == "Awaiting Fulfillment" and o["total"] == "80.0000" and o["currency"] == "USD" and o["created_at"].startswith("Wed, 13 Mar 2019")
    req = respx.calls.last.request
    assert req.headers["X-Auth-Token"] == "tok" and "Authorization" not in req.headers
    assert req.url.params["status_id"] == "11" and req.url.params["min_date_created"] == "2019-03-01T00:00:00.000-04:00" and req.url.params["page"] == "1" and req.url.params["limit"] == "50"


@pytest.mark.asyncio
@respx.mock
async def test_set_inventory_puts_product_level_tracking_and_reads_the_data_envelope():
    # docs.bigcommerce.com .../catalog/products/update-product -> {data: product, meta: {}}
    route = respx.put("https://api.bigcommerce.com/stores/abc123/v3/catalog/products/174").mock(return_value=httpx.Response(200, json={
        "data": {"id": 174, "name": "Smith Journal 13", "type": "physical", "sku": "SM-13", "price": 25, "inventory_level": 5, "inventory_tracking": "product", "availability": "available"}, "meta": {}}))
    res = await _server().call_tool("set_inventory", {"listing_id": "174", "quantity": 5})
    assert res.is_error is False and res.structured_content["status"] == "updated" and res.structured_content["raw"]["inventory_level"] == 5
    assert json.loads(route.calls.last.request.content) == {"inventory_tracking": "product", "inventory_level": 5}


@pytest.mark.asyncio
@respx.mock
async def test_end_listing_hides_the_product_with_a_json_boolean():
    route = respx.put("https://api.bigcommerce.com/stores/abc123/v3/catalog/products/174").mock(return_value=httpx.Response(200, json={"data": {"id": 174, "is_visible": False, "availability": "available"}, "meta": {}}))
    res = await _server().call_tool("end_listing", {"listing_id": "174"})
    assert res.is_error is False and res.structured_content["status"] == "hidden" and res.structured_content["raw"]["is_visible"] is False
    assert json.loads(route.calls.last.request.content) == {"is_visible": False}


@pytest.mark.asyncio
@respx.mock
async def test_create_listing_posts_the_documented_required_fields_with_a_numeric_weight():
    # docs.bigcommerce.com .../catalog/products/create-product: required name, type, weight, price; example {"name": "Smith Journal 13", "type": "physical", "weight": 0, "price": 0}
    route = respx.post("https://api.bigcommerce.com/stores/abc123/v3/catalog/products").mock(return_value=httpx.Response(200, json={
        "data": {"id": 174, "name": "Smith Journal 13", "type": "physical", "sku": "SM-13", "weight": 0, "price": 25, "availability": "available", "is_visible": True,
                 "inventory_level": 5, "inventory_tracking": "none", "custom_url": {"url": "/smith-journal-13/", "is_customized": False}}, "meta": {}}))
    res = await _server().call_tool("create_listing", {"title": "Smith Journal 13", "price": 25, "sku": "SM-13", "quantity": 5, "description": "<p>Journal</p>"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["listing_id"] == "174" and sc["url"] == "/smith-journal-13/" and sc["status"] == "available"
    assert json.loads(route.calls.last.request.content) == {"name": "Smith Journal 13", "type": "physical", "weight": 0, "price": 25, "sku": "SM-13", "description": "<p>Journal</p>", "inventory_level": 5}


@pytest.mark.asyncio
@respx.mock
async def test_mark_shipped_sets_status_id_2_as_an_integer():
    # docs.bigcommerce.com .../management/orders/update-order -> the order; status id 2 = Shipped (GET /v2/order_statuses)
    route = respx.put("https://api.bigcommerce.com/stores/abc123/v2/orders/100").mock(return_value=httpx.Response(200, json={"id": 100, "status_id": 2, "status": "Shipped", "total_inc_tax": "80.0000"}))
    res = await _server().call_tool("mark_shipped", {"order_id": "100", "carrier": "usps", "tracking_number": "EJ958083578US"})
    assert res.is_error is False and res.structured_content["status"] == "Shipped"
    assert json.loads(route.calls.last.request.content) == {"status_id": 2}  # tracking is not recorded (shipments need items[] from the order)


@pytest.mark.asyncio
@respx.mock
async def test_empty_order_list_is_a_204_and_yields_no_orders():
    respx.get("https://api.bigcommerce.com/stores/abc123/v2/orders").mock(return_value=httpx.Response(204))
    res = await _server().call_tool("list_orders", {})
    assert res.is_error is False and res.structured_content["orders"] == [] and res.structured_content["next_page"] is None


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_is_error_result():
    respx.get("https://api.bigcommerce.com/stores/abc123/v2/store").mock(return_value=httpx.Response(429, headers={"Retry-After": "30"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 30
