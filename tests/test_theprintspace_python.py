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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "theprintspace.json").read_text(encoding="utf-8"))
BASE = "https://escher-v2.creativehub.io/v1"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {"api_token": "chub_tok_123"}, 50, "test"))


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary():
    tools = {t.name: t for t in await _server().list_tools()}
    assert sorted(tools) == ["create_order", "get_order", "get_product", "list_products", "me", "quote_shipping"]
    assert tools["create_order"].annotations.destructive_hint is True


@pytest.mark.asyncio
@respx.mock
async def test_list_products_pages_with_limit_offset_and_bearer():
    route = respx.get(f"{BASE}/products").mock(return_value=httpx.Response(200, json={"products": [
        {"id": "p1", "name": "Sunset No. 4", "artwork_thumbnail_url": "https://cdn/x.jpg", "variant_count": 2}], "limit": 10, "offset": 10}))
    res = await _server().call_tool("list_products", {"page": 2, "limit": 10})
    assert res.is_error is False
    assert res.structured_content["products"][0]["id"] == "p1" and res.structured_content["products"][0]["title"] == "Sunset No. 4"
    req = route.calls.last.request
    assert req.url.params["limit"] == "10" and req.url.params["offset"] == "10"
    assert req.headers["Authorization"] == "Bearer chub_tok_123"


@pytest.mark.asyncio
@respx.mock
async def test_get_product_and_quote_use_the_variant():
    respx.get(f"{BASE}/products/p1").mock(return_value=httpx.Response(200, json={"id": "p1", "name": "Sunset No. 4", "artwork_url": "https://cdn/a.jpg",
        "variants": [{"id": "v9", "sku": "CH-1", "retail_price": 120, "price_currency": "GBP"}]}))
    quote = respx.post(f"{BASE}/orders/quote").mock(return_value=httpx.Response(200, json={"currency": "GBP", "total_incl_vat": 54.0, "total_excl_vat": 45.0,
        "total_vat": 9.0, "production_cost": 35.0, "delivery_cost": 10.0, "addon_cost": 0, "ddp_total": 0}))
    s = _server()
    p = (await s.call_tool("get_product", {"id": "p1"})).structured_content
    assert p["price"] == 120 and p["currency"] == "GBP" and p["sku"] == "CH-1"
    q = (await s.call_tool("quote_shipping", {"product_id": "v9", "country": "US", "quantity": 2})).structured_content
    assert q["options"][0]["delivery_cost"] == 10.0 and q["options"][0]["total_incl_vat"] == 54.0
    assert json.loads(quote.calls.last.request.content) == {"items": [{"variant_id": "v9", "quantity": 2}], "delivery_country_code": "US"}


@pytest.mark.asyncio
@respx.mock
async def test_create_order_maps_the_delivery_fields():
    route = respx.post(f"{BASE}/orders").mock(return_value=httpx.Response(201, json={"order_id": "o1", "order_number": "CH1001", "currency": "GBP", "total_incl_vat": 54.0, "lines": []}))
    res = await _server().call_tool("create_order", {"items": [{"variant_id": "v9", "quantity": 1}], "shipping_address": {
        "name": "Ada Lovelace", "address1": "1 Main St", "city": "London", "postcode": "N1 1AA", "country_code": "GB"}})
    assert res.is_error is False and res.structured_content["id"] == "o1" and res.structured_content["total"] == 54.0
    body = json.loads(route.calls.last.request.content)
    assert body == {"items": [{"variant_id": "v9", "quantity": 1}], "delivery_name": "Ada Lovelace", "delivery_line1": "1 Main St",
                    "delivery_city": "London", "delivery_postcode": "N1 1AA", "delivery_country_code": "GB"}


@pytest.mark.asyncio
@respx.mock
async def test_forbidden_is_an_auth_error_without_the_token():
    respx.get(f"{BASE}/orders/o1").mock(return_value=httpx.Response(403, json={"detail": "API access disabled"}))
    res = await _server().call_tool("get_order", {"id": "o1"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "chub_tok_123" not in json.dumps(res.structured_content)
