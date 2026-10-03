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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "vidaxl_dropshipping.json").read_text(encoding="utf-8"))
BASE = "https://b2b.vidaxl.com/api_customer"
CREDS = {"email": "shop@example.com", "api_token": "tok"}


def _server(creds=None):
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], creds or CREDS, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
@respx.mock
async def test_list_products_uses_basic_auth_and_limit_offset():
    respx.get(f"{BASE}/products").mock(return_value=httpx.Response(200, json=[
        {"id": 4, "name": "vidaXL Cat Tree 182 cm Beige Plush", "code": "100058", "category_path": "Animals & Pet Supplies/Cat Furniture", "quantity": "0.0", "price": "75.00"}]))
    res = await _server().call_tool("list_products", {"page": 3, "limit": 50})
    assert res.is_error is False
    p = res.structured_content["products"][0]
    assert p["id"] == "100058" and p["title"] == "vidaXL Cat Tree 182 cm Beige Plush" and p["list_price"] == "75.00" and p["product_id"] == "4"
    req = respx.calls.last.request
    assert req.url.params["limit"] == "50" and req.url.params["offset"] == "100"
    assert req.headers["Authorization"].startswith("Basic ")


@pytest.mark.asyncio
@respx.mock
async def test_get_product_filters_by_code_and_empty_is_not_found():
    respx.get(f"{BASE}/products", params={"code_eq": "100058"}).mock(return_value=httpx.Response(200, json=[{"id": 4, "name": "Cat Tree", "code": "100058", "price": "75.00"}]))
    respx.get(f"{BASE}/products", params={"code_eq": "0"}).mock(return_value=httpx.Response(200, json=[]))
    res = await _server().call_tool("get_product", {"id": "100058"})
    assert res.structured_content["title"] == "Cat Tree"
    res = await _server().call_tool("get_product", {"id": "0"})
    assert res.is_error is True and res.structured_content["error"] == "not_found"


@pytest.mark.asyncio
@respx.mock
async def test_create_order_sends_addressbook_and_order_products():
    route = respx.post(f"{BASE}/orders").mock(return_value=httpx.Response(200, json={"order": {"id": 70, "status_order_id": 1, "created_at": "2018-06-08T03:47:48.000-04:00", "gross_total": "95.97", "customer_order_reference": "x"}, "order_products": []}))
    addr = {"name": "Test Company", "address": "Covent Garden 1", "city": "London", "postal_code": "NR33 7NL", "country": "GB", "phone": "0684541247"}
    res = await _server().call_tool("create_order", {"items": [{"product_code": "274181", "quantity": 1}], "shipping_address": addr})
    assert res.is_error is False and res.structured_content["id"] == "70"
    body = json.loads(route.calls.last.request.content)
    assert body["addressbook"] == addr and body["order_products"] == [{"product_code": "274181", "quantity": 1}] and len(body["customer_order_reference"]) == 36


@pytest.mark.asyncio
@respx.mock
async def test_get_order_reads_the_nested_order():
    respx.get(f"{BASE}/orders").mock(return_value=httpx.Response(200, json=[{"order": {
        "id": "B2B111", "status_order_id": 5, "status_order_name": "Sent", "submitted_at": "2019-04-30T15:35:05.000+02:00", "shipping_tracking": "TEST9999", "gross_total": "3.6648"}}]))
    res = await _server().call_tool("get_order", {"id": "B2B111"})
    sc = res.structured_content
    assert sc["id"] == "B2B111" and sc["status"] == "Sent" and sc["tracking_number"] == "TEST9999"
    assert respx.calls.last.request.url.params["id_eq"] == "B2B111"
