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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "matterhorn.json").read_text(encoding="utf-8"))
BASE = "https://matterhorn-wholesale.com/B2BAPI"


def _server(**extra):
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": "mh-key-777", **extra}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["create_order", "get_order", "get_product", "list_products", "me"]


@pytest.mark.asyncio
@respx.mock
async def test_get_product_maps_the_documented_item():
    route = respx.get(f"{BASE}/ITEMS/186365").mock(return_value=httpx.Response(200, json={
        "id": "186365", "name": " Daydress model 186365 Top Secret ", "stock_total": 172, "url": "http://matterhorn-wholesale.com/daydress_no_186365_prod_id-186365.htm",
        "images": ["http://matterhorn-wholesale.com/db_images/custom900x1200_997785.jpg"], "prices": {"EUR": 12.9, "USD": 13.9}, "brand": "Top Secret",
        "variants": [{"variant_uid": "1090549", "name": "34", "stock": "35"}]}))
    res = await _server().call_tool("get_product", {"id": "186365"})
    sc = res.structured_content
    assert sc["price"] == 12.9 and sc["currency"] == "EUR" and sc["stock"] == 172 and sc["image_url"].endswith("997785.jpg")
    assert route.calls.last.request.headers["Authorization"] == "mh-key-777"


@pytest.mark.asyncio
@respx.mock
async def test_create_order_uses_put_with_delivery_method_id():
    route = respx.put(f"{BASE}/ACCOUNT/ORDERS/").mock(return_value=httpx.Response(200, json={"id": "67062", "order_date": "2023-10-04 09:14:07", "status": "New order", "order_currency": "EUR", "total_gross": 95.86, "payment_url": "https://matterhorn-wholesale.com/rwd_checkout.php?order_ext=67062"}))
    res = await _server(currency="EUR").call_tool("create_order", {"items": [{"variant_uid": 1090551, "quantity": 4}],
        "shipping_address": {"first_name": "John", "second_name": "Smith", "country": "de", "street": "Musterstraße", "house_number": "123", "zip": "10115", "city": "Berlin"}, "shipping_option": "160"})
    assert res.structured_content["id"] == "67062" and res.structured_content["total"] == 95.86
    body = json.loads(route.calls.last.request.content)
    assert body["delivery_method_id"] == 160 and body["currency"] == "EUR" and body["items"] == [{"variant_uid": 1090551, "quantity": 4}] and body["delivery_to"]["zip"] == "10115"


@pytest.mark.asyncio
@respx.mock
async def test_refused_key_is_an_auth_error_without_the_key():
    respx.get(f"{BASE}/DICTIONARIES/CATEGORIES").mock(return_value=httpx.Response(401, text="invalid key mh-key-777"))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and "mh-key-777" not in json.dumps(res.structured_content)
