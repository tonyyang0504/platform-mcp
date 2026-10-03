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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "contrado.json").read_text(encoding="utf-8"))
BASE = "https://api.contrado.app/helix/v1"


def _server(creds=None):
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], creds or {"api_key": "k"}, 50, "test", envelope=a.get("envelope"))
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_order", "get_product", "list_products", "me"]
    assert set(SPEC["adapter"]["not_offered"]) == {"create_order", "quote_shipping", "track"}


@pytest.mark.asyncio
@respx.mock
async def test_list_products_unwraps_the_envelope_and_sends_the_store_id():
    respx.get(f"{BASE}/stores/products").mock(return_value=httpx.Response(200, json={
        "success": True, "message": "Request Successful",
        "data": [{"storeProductId": 591879, "baseProductId": 12, "storeProductName": "Silk Scarf", "productThumb": "https://static.test/t.jpeg", "storeProductURL": "https://s.test/p", "isOutOfStock": False}],
        "error": None}))
    res = await _server({"api_key": "k", "store_id": "88"}).call_tool("list_products", {"page": 3, "limit": 20})
    assert res.is_error is False
    p = res.structured_content["products"][0]
    assert p["id"] == "591879" and p["title"] == "Silk Scarf" and p["image_url"] == "https://static.test/t.jpeg"
    req = respx.calls.last.request
    assert req.url.params["PageNumber"] == "3" and req.url.params["PageSize"] == "20"
    assert req.headers["X-API-KEY"] == "k" and req.headers["X-Store-Id"] == "88"


@pytest.mark.asyncio
@respx.mock
async def test_get_order_reads_data_and_omits_store_header_when_unset():
    respx.get(f"{BASE}/orders/1234").mock(return_value=httpx.Response(200, json={"success": True, "data": {
        "orderId": 1234, "orderStatus": "Dispatched", "referenceId": "3fa85f64-5717-4562-b3fc-2c963f66afa6", "orderedUtcDateTime": "2026-09-01T10:00:00Z",
        "trackingId": "RM123", "trackingUrl": "https://rm.test/RM123", "totalPrice": 42.5, "currencyCode": "GBP"}}))
    res = await _server().call_tool("get_order", {"id": "1234"})
    sc = res.structured_content
    assert sc["id"] == "1234" and sc["status"] == "Dispatched" and sc["total"] == 42.5 and sc["currency"] == "GBP" and sc["tracking_number"] == "RM123"
    assert "X-Store-Id" not in respx.calls.last.request.headers


@pytest.mark.asyncio
@respx.mock
async def test_failure_inside_a_200_envelope_is_an_error_result():
    respx.get(f"{BASE}/stores").mock(return_value=httpx.Response(200, json={"success": False, "message": "Invalid argument provided", "data": None}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error"
