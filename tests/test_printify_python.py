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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "printify.json").read_text(encoding="utf-8"))


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"token": "t", "shop_id": "8765"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["create_order", "get_order", "get_product", "list_products", "me"]  # quote_shipping/track not offered
    lp = next(t for t in tools if t.name == "list_products")
    assert lp.annotations.read_only_hint is True and lp.output_schema["properties"]["products"]["type"] == "array"
    assert lp.meta["platform_mcp/endpoint"] == "/catalog/blueprints.json"


@pytest.mark.asyncio
@respx.mock
async def test_list_products_maps_catalog_blueprints():
    # developers.printify.com Catalog: GET /v1/catalog/blueprints.json -> [{id, title, brand, model, images[]}]
    respx.get("https://api.printify.com/v1/catalog/blueprints.json").mock(return_value=httpx.Response(200, json=[
        {"id": 3, "title": "Kids Regular Fit Tee", "description": "...", "brand": "Delta", "model": "11736", "images": ["https://images.printify.com/5853fe7dce46f30f8327f5cd", "https://images.printify.com/5c487ee2a342bc9b8b2fc4d2"]},
    ]))
    res = await _server().call_tool("list_products", {})
    assert res.is_error is False
    p = res.structured_content["products"][0]
    assert p["id"] == "3" and p["title"] == "Kids Regular Fit Tee" and p["image_url"].endswith("f5cd") and p["brand"] == "Delta"
    assert res.structured_content["next_page"] is None  # unpaginated catalogue
    assert respx.calls.last.request.headers["Authorization"] == "Bearer t"


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_is_error_result():
    respx.get("https://api.printify.com/v1/catalog/blueprints/3.json").mock(return_value=httpx.Response(429, headers={"Retry-After": "60"}))
    res = await _server().call_tool("get_product", {"id": "3"})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 60


@pytest.mark.asyncio
@respx.mock
async def test_get_order_takes_the_shop_id_from_the_install_config():
    # developers.printify.com Orders: GET /v1/shops/{shop_id}/orders/{order_id}.json
    respx.get("https://api.printify.com/v1/shops/8765/orders/5a96f649b2439217d070f507.json").mock(return_value=httpx.Response(200, json={
        "id": "5a96f649b2439217d070f507", "status": "fulfilled", "total_price": 2200, "total_shipping": 400, "created_at": "2017-04-18 13:24:28+00:00",
        "shipments": [{"carrier": "usps", "number": "94001116990045395649372", "url": "http://example.com/94001116990045395649372", "delivered_at": "2017-04-18 13:24:28+00:00"}]}))
    res = await _server().call_tool("get_order", {"id": "5a96f649b2439217d070f507"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["status"] == "fulfilled" and sc["total"] == 2200 and sc["tracking_number"] == "94001116990045395649372" and sc["tracking_url"].startswith("http://example.com/")


@pytest.mark.asyncio
@respx.mock
async def test_create_order_posts_the_documented_body_without_sending_to_production():
    route = respx.post("https://api.printify.com/v1/shops/8765/orders.json").mock(return_value=httpx.Response(200, json={"id": "5a96f649b2439217d070f507"}))
    res = await _server().call_tool("create_order", {"items": [{"product_id": "5bfd0b66a342bcc9b5563216", "variant_id": 17887, "quantity": 1}],
                                                       "shipping_address": {"first_name": "J", "last_name": "D", "email": "j@example.com", "phone": "1", "country": "US", "region": "CA", "address1": "1 St", "city": "LA", "zip": "90001"},
                                                       "shipping_option": 1})
    assert res.is_error is False and res.structured_content["id"] == "5a96f649b2439217d070f507"
    body = json.loads(route.calls.last.request.content)
    assert body["line_items"][0]["variant_id"] == 17887 and body["address_to"]["country"] == "US" and body["shipping_method"] == 1
    assert len(route.calls) == 1  # no send_to_production call
