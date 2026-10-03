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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "customcat.json").read_text(encoding="utf-8"))
BASE = "https://customcat-beta.mylocker.net/api/v1"


def _server(creds=None):
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], creds or {"api_key": "k"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
@respx.mock
async def test_list_products_reads_nested_product_and_sends_the_key_as_a_parameter():
    respx.get(f"{BASE}/product").mock(return_value=httpx.Response(200, json={"products": [{"product": {
        "product_id": "22-2580581", "title": "Custom Ultra Cotton T-Shirt", "product_type": "T-Shirts",
        "variants": [{"sku": "22-109-2580581-248", "price": 19.95, "cost": 6, "instock": "true"}]}}]}))
    res = await _server().call_tool("list_products", {"limit": 10})
    assert res.is_error is False
    p = res.structured_content["products"][0]
    assert p["id"] == "22-2580581" and p["sku"] == "22-109-2580581-248" and p["price"] == 19.95
    req = respx.calls.last.request
    assert req.url.params["api_key"] == "k" and req.url.params["limit"] == "10"


@pytest.mark.asyncio
@respx.mock
async def test_create_order_flattens_the_address_under_a_fresh_order_id():
    route = respx.post(url__regex=rf"{BASE}/order/[0-9a-f-]{{36}}").mock(return_value=httpx.Response(200, json={
        "ORDER_ID": "abc", "MSG": "Order added successfully", "CUSTOMCAT_ORDER_ID": "184DEF43-CB85"}))
    addr = {"first_name": "Joe", "last_name": "Testing", "email": "no-email@customcat.com", "phone": "555", "address1": "1300 Rosa Parks Blvd", "city": "Detroit", "state": "MI", "zip": "48216", "country": "US"}
    res = await _server({"api_key": "k", "sandbox": "1"}).call_tool("create_order", {"items": [{"sku": "22-115-4774-254", "quantity": 1}], "shipping_address": addr, "shipping_option": "Economy"})
    assert res.is_error is False and res.structured_content["customcat_order_id"] == "184DEF43-CB85"
    body = json.loads(route.calls.last.request.content)
    assert body["shipping_first_name"] == "Joe" and body["shipping_zip"] == "48216" and body["shipping_method"] == "Economy"
    assert body["sandbox"] == "1" and body["items"] == [{"sku": "22-115-4774-254", "quantity": 1}] and "shipping_address2" not in body


@pytest.mark.asyncio
@respx.mock
async def test_get_order_and_track_read_the_status_record():
    payload = {"ORDER_ID": "TestOrder1", "ORDER_STATUS": "Shipped", "ORDER_TOTAL": 19.47, "ORDER_DATE": "March, 27 2018 12:14:45",
               "CUSTOMCAT_ORDER_ID": "C26B", "SHIPMENTS": [{"TRACKING_ID": "9274890", "METHOD": "Expedited Mail Innovations", "VENDOR": "UPS", "NUMBER_ITEMS": 1}]}
    respx.get(f"{BASE}/order/status/TestOrder1").mock(return_value=httpx.Response(200, json=payload))
    res = await _server().call_tool("get_order", {"id": "TestOrder1"})
    assert res.structured_content["status"] == "Shipped" and res.structured_content["total"] == 19.47 and res.structured_content["tracking_number"] == "9274890"
    res = await _server().call_tool("track", {"order_id": "TestOrder1"})
    assert res.structured_content["events"][0]["carrier"] == "UPS"


@pytest.mark.asyncio
@respx.mock
async def test_read_only_key_on_write_is_an_auth_error():
    respx.post(url__regex=rf"{BASE}/order/.*").mock(return_value=httpx.Response(403, headers={"X-FAIL-MESSAGE": "read-only key"}))
    res = await _server().call_tool("create_order", {"items": [], "shipping_address": {}})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
