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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "printful.json").read_text(encoding="utf-8"))


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"token": "t"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["create_order", "get_order", "get_product", "list_products", "me"]
    co = next(t for t in tools if t.name == "create_order")
    assert co.annotations.read_only_hint is False and co.annotations.destructive_hint is True
    assert co.input_schema["required"] == ["items", "shipping_address"]
    lp = next(t for t in tools if t.name == "list_products")
    assert lp.annotations.read_only_hint is True and lp.meta["platform_mcp/endpoint"] == "/products"


@pytest.mark.asyncio
@respx.mock
async def test_list_products_maps_result_and_paging():
    # developers.printful.com Catalog API: GET /products -> {code, result: [...], paging: {total, offset, limit}}
    respx.get("https://api.printful.com/products").mock(return_value=httpx.Response(200, json={
        "code": 200,
        "result": [{"id": 71, "type": "T-SHIRT", "type_name": "T-Shirt", "title": "Unisex Staple T-Shirt | Bella + Canvas 3001", "brand": "Bella + Canvas", "model": "3001", "image": "https://files.cdn.printful.com/products/71/product_1581412541.jpg", "variant_count": 396, "currency": "USD"}],
        "paging": {"total": 1, "offset": 0, "limit": 20}}))
    res = await _server().call_tool("list_products", {"category": "24"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["products"][0]["id"] == "71" and sc["products"][0]["currency"] == "USD" and sc["products"][0]["variant_count"] == 396
    assert sc["total"] is None  # auth audit: the catalog answers the whole list, with no paging object
    req = respx.calls.last.request
    assert "offset" not in req.url.params and "limit" not in req.url.params and req.url.params["category_id"] == "24"
    assert req.headers["Authorization"] == "Bearer t"


@pytest.mark.asyncio
@respx.mock
async def test_create_order_sends_the_documented_body_and_stays_a_draft():
    route = respx.post("https://api.printful.com/orders").mock(return_value=httpx.Response(200, json={
        "code": 200, "result": {"id": 13, "status": "draft", "shipping": "STANDARD", "created": 1602000000, "costs": {"currency": "USD", "total": "27.24"}, "shipments": []}}))
    res = await _server().call_tool("create_order", {"items": [{"variant_id": 4011, "quantity": 1, "files": [{"url": "https://example.com/a.png"}]}],
                                                       "shipping_address": {"name": "J", "address1": "1 St", "city": "LA", "state_code": "CA", "country_code": "US", "zip": "90001"}})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["id"] == "13" and sc["status"] == "draft" and sc["total"] == "27.24" and sc["currency"] == "USD" and sc["tracking_number"] is None
    req = route.calls.last.request
    assert "confirm" not in req.url.params  # never auto-confirms (no money spent)
    body = json.loads(req.content)
    assert body["items"][0]["variant_id"] == 4011 and body["recipient"]["country_code"] == "US" and "shipping" not in body


@pytest.mark.asyncio
@respx.mock
async def test_bad_token_is_an_auth_error_result():
    respx.get("https://api.printful.com/oauth/scopes").mock(return_value=httpx.Response(401, json={"code": 401, "result": "Unauthorized"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
