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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "abound.json").read_text(encoding="utf-8"))
PRODUCT = {"id": "5f1", "title": "Ceramic Mug", "brand": "Acme", "companyId": "c1",
           "images": [{"id": "i1", "position": 0, "source": "https://cdn.example.com/mug.jpg"}],
           "variants": [{"id": "v1", "sku": "MUG-1", "basePrice": 6.5, "baseCurrency": "USD", "retailPrice": 14, "inventoryAmount": 120}]}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": "k"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_order", "get_product", "list_products", "me"]
    lp = next(t for t in tools if t.name == "list_products")
    assert lp.annotations.read_only_hint is True and lp.annotations.destructive_hint is False
    assert lp.meta["platform_mcp/endpoint"] == "/buyer/products"
    assert lp.meta["platform_mcp/docs"] == "https://developers.moderndropship.com/openapi/buyer-api.json"
    assert "create_order" in SPEC["adapter"]["not_offered"]


@pytest.mark.asyncio
@respx.mock
async def test_list_products_unwraps_data_and_sends_the_raw_api_key_header():
    # developers.moderndropship.com buyer-api: GET /buyer/products -> {data: [...], hasMore}
    respx.get("https://api.moderndropship.com/buyer/products").mock(return_value=httpx.Response(200, json={"data": [PRODUCT], "hasMore": False}))
    res = await _server().call_tool("list_products", {"query": "mug", "page": 3, "limit": 20})
    assert res.is_error is False
    p = res.structured_content["products"][0]
    assert p["id"] == "5f1" and p["title"] == "Ceramic Mug" and p["image_url"] == "https://cdn.example.com/mug.jpg"
    assert p["price"] == 6.5 and p["currency"] == "USD" and p["sku"] == "MUG-1" and p["stock"] == 120 and p["brand"] == "Acme"
    assert res.structured_content["next_page"] is None
    req = respx.calls.last.request
    assert req.url.params["page"] == "2" and req.url.params["limit"] == "20" and req.url.params["title"] == "mug"
    assert "companyId" not in req.url.params
    assert req.headers["Authorization"] == "k"  # raw key, no Bearer prefix


@pytest.mark.asyncio
@respx.mock
async def test_get_product_reads_the_data_envelope():
    respx.get("https://api.moderndropship.com/buyer/products/5f1").mock(return_value=httpx.Response(200, json={"data": PRODUCT}))
    res = await _server().call_tool("get_product", {"id": "5f1"})
    assert res.is_error is False
    assert res.structured_content["id"] == "5f1" and res.structured_content["raw"]["variants"][0]["id"] == "v1"


@pytest.mark.asyncio
@respx.mock
async def test_get_order_reads_the_first_fulfillment_tracking_code():
    respx.get("https://api.moderndropship.com/buyer/orders/o1").mock(return_value=httpx.Response(200, json={"data": {
        "id": "o1", "buyerReference": "shop-1001", "created": "2026-09-01T10:00:00Z",
        "sellerOrders": [{"id": "so1", "posted": True, "fulfilled": True, "fulfillments": [{"carrier": "UPS", "trackingCode": "1Z999", "trackingUrls": ["https://ups.example/1Z999"]}]}]}}))
    res = await _server().call_tool("get_order", {"id": "o1"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["id"] == "o1" and sc["created_at"] == "2026-09-01T10:00:00Z" and sc["tracking_number"] == "1Z999"


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_error_result():
    respx.get("https://api.moderndropship.com/auth/me").mock(return_value=httpx.Response(429, headers={"Retry-After": "5"}, json={"error": [{"message": "rate limited"}]}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 5
