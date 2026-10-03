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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "gelato.json").read_text(encoding="utf-8"))
UID = "cards_pf_bb_pt_110-lb-cover-uncoated_cl_4-0_hor"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": "k"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_order", "get_product", "list_products", "me"]
    go = next(t for t in tools if t.name == "get_order")
    assert go.annotations.read_only_hint is True and go.meta["platform_mcp/endpoint"] == "/v4/orders/{orderId}"
    assert go.meta["platform_mcp/docs"] == "https://dashboard.gelato.com/docs/orders/v4/get/"
    assert set(SPEC["adapter"]["not_offered"]) == {"create_order", "quote_shipping", "track"}


@pytest.mark.asyncio
@respx.mock
async def test_list_products_searches_the_catalog_on_the_product_host():
    # dashboard.gelato.com/docs/products/product/search: POST /v3/catalogs/{catalogUid}/products:search -> {products, hits}
    route = respx.post(f"https://product.gelatoapis.com/v3/catalogs/posters/products:search").mock(return_value=httpx.Response(200, json={
        "products": [{"productUid": UID, "attributes": {"Orientation": "hor"}, "weight": {"value": 12.3, "measureUnit": "grams"}}], "hits": {"attributeHits": {}}}))
    res = await _server().call_tool("list_products", {"category": "posters", "page": 2, "limit": 50})
    assert res.is_error is False
    p = res.structured_content["products"][0]
    assert p["id"] == UID and p["title"] == UID and p["raw"]["attributes"]["Orientation"] == "hor"
    req = route.calls.last.request
    assert json.loads(req.content) == {"limit": 50, "offset": 50}
    assert req.headers["X-API-KEY"] == "k" and "Authorization" not in req.headers


@pytest.mark.asyncio
async def test_list_products_needs_a_catalog_uid():
    res = await _server().call_tool("list_products", {"query": "poster"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input"


@pytest.mark.asyncio
@respx.mock
async def test_get_order_maps_status_total_and_tracking():
    respx.get("https://order.gelatoapis.com/v4/orders/37365096").mock(return_value=httpx.Response(200, json={
        "id": "37365096", "orderType": "order", "orderReferenceId": "my-1", "fulfillmentStatus": "printed", "financialStatus": "paid", "currency": "USD",
        "createdAt": "2021-01-14T10:32:03+00:00", "items": [],
        "shipment": {"shipmentMethodUid": "ups_surepost", "packages": [{"trackingCode": "12345678990", "trackingUrl": "http://test.tracking.url"}]},
        "receipts": [{"transactionType": "purchase", "currency": "USD", "totalInclVat": 33.45}]}))
    res = await _server().call_tool("get_order", {"id": "37365096"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["id"] == "37365096" and sc["status"] == "printed" and sc["total"] == 33.45 and sc["currency"] == "USD"
    assert sc["created_at"] == "2021-01-14T10:32:03+00:00" and sc["tracking_number"] == "12345678990"


@pytest.mark.asyncio
@respx.mock
async def test_bad_key_is_an_auth_error_result():
    respx.get("https://product.gelatoapis.com/v3/catalogs").mock(return_value=httpx.Response(401, json={"message": "Unauthorized"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
