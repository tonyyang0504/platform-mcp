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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "woocommerce.json").read_text(encoding="utf-8"))
BASIC = "Basic " + base64.b64encode(b"ck_key:cs_secret").decode()


def _server():
    # store_host is a non-secret config field: every tool path is https://{store_host}/wp-json/wc/v3/...
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"consumer_key": "ck_key", "consumer_secret": "cs_secret", "store_host": "shop.example"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_channel_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["create_listing", "end_listing", "list_orders", "mark_shipped", "me", "set_inventory", "update_listing"]  # listing_metrics not offered
    cl = next(t for t in tools if t.name == "create_listing")
    assert cl.annotations.read_only_hint is False and cl.annotations.destructive_hint is False and cl.input_schema["required"] == ["title", "price"]
    el = next(t for t in tools if t.name == "end_listing")
    assert el.annotations.destructive_hint is True
    lo = next(t for t in tools if t.name == "list_orders")
    assert lo.annotations.read_only_hint is True and lo.output_schema["properties"]["orders"]["type"] == "array"
    assert lo.meta["platform_mcp/endpoint"] == "https://{store_host}/wp-json/wc/v3/orders"


@pytest.mark.asyncio
@respx.mock
async def test_create_listing_posts_the_documented_product_body_to_the_configured_store():
    # woocommerce.github.io/woocommerce-rest-api-docs/#create-a-product -> the created product
    route = respx.post("https://shop.example/wp-json/wc/v3/products").mock(return_value=httpx.Response(201, json={
        "id": 794, "name": "Premium Quality", "slug": "premium-quality-19", "permalink": "https://shop.example/product/premium-quality-19/",
        "date_created": "2017-03-23T17:01:14", "type": "simple", "status": "publish", "description": "<p>Pellentesque habitant morbi</p>\n",
        "sku": "PQ-1", "price": "21.99", "regular_price": "21.99", "sale_price": "", "manage_stock": True, "stock_quantity": 10, "stock_status": "instock"}))
    res = await _server().call_tool("create_listing", {"title": "Premium Quality", "price": 21.99, "description": "Pellentesque habitant morbi", "sku": "PQ-1", "quantity": 10})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["listing_id"] == "794" and sc["url"].endswith("/premium-quality-19/") and sc["status"] == "publish"
    req = route.calls.last.request
    assert json.loads(req.content) == {"name": "Premium Quality", "type": "simple", "regular_price": "21.99", "description": "Pellentesque habitant morbi", "sku": "PQ-1", "stock_quantity": 10, "manage_stock": True}  # str:price -> documented decimal string; json:true -> boolean
    assert req.headers["Authorization"] == BASIC  # consumer key : consumer secret as HTTP Basic over https


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_sends_the_documented_query_and_maps_the_order_record():
    # woocommerce.github.io/woocommerce-rest-api-docs/#list-all-orders
    respx.get("https://shop.example/wp-json/wc/v3/orders").mock(return_value=httpx.Response(200, json=[
        {"id": 727, "parent_id": 0, "number": "727", "order_key": "wc_order_58d2d042d1d", "status": "processing", "currency": "USD", "version": "3.0.0",
         "date_created": "2017-03-22T16:28:02", "total": "29.35", "total_tax": "1.35", "customer_id": 0, "line_items": [{"id": 315, "name": "Woo Single #1", "product_id": 93, "quantity": 2}]}]))
    res = await _server().call_tool("list_orders", {"status": "processing", "since": "2017-03-01T00:00:00", "page": 2, "limit": 50})
    assert res.is_error is False
    o = res.structured_content["orders"][0]
    assert o["id"] == "727" and o["status"] == "processing" and o["total"] == "29.35" and o["currency"] == "USD" and o["created_at"] == "2017-03-22T16:28:02"
    assert res.structured_content["total"] is None and res.structured_content["next_page"] is None  # one record < per_page
    params = respx.calls.last.request.url.params
    assert params["page"] == "2" and params["per_page"] == "50" and params["status"] == "processing" and params["after"] == "2017-03-01T00:00:00"


@pytest.mark.asyncio
@respx.mock
async def test_mark_shipped_sets_status_completed_without_inventing_tracking_fields():
    route = respx.put("https://shop.example/wp-json/wc/v3/orders/727").mock(return_value=httpx.Response(200, json={"id": 727, "status": "completed", "currency": "USD", "total": "29.35"}))
    res = await _server().call_tool("mark_shipped", {"order_id": "727", "carrier": "usps", "tracking_number": "9400"})
    assert res.is_error is False and res.structured_content["status"] == "completed"
    assert json.loads(route.calls.last.request.content) == {"status": "completed"}  # core WooCommerce has no tracking fields


@pytest.mark.asyncio
@respx.mock
async def test_set_inventory_needs_the_product_id_and_bad_keys_are_an_auth_error_result():
    res = await _server().call_tool("set_inventory", {"sku": "PQ-1", "quantity": 3})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input" and "listing_id" in res.structured_content["message"]
    respx.get("https://shop.example/wp-json/wc/v3/system_status").mock(return_value=httpx.Response(401, json={"code": "woocommerce_rest_cannot_view", "message": "Sorry, you cannot list resources.", "data": {"status": 401}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 401
