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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "spreadconnect.json").read_text(encoding="utf-8"))
BASE = "https://api.spreadconnect.app"


def _server(creds=None):
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], creds or {"access_token": "tok"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_order", "get_product", "list_products", "me", "track"]
    assert all(t.annotations.read_only_hint is True for t in tools)


@pytest.mark.asyncio
@respx.mock
async def test_list_products_uses_limit_offset_and_the_token_header():
    # api.spreadconnect.app/docs getArticles: {items[Article], count, limit, offset}
    respx.get(f"{BASE}/articles").mock(return_value=httpx.Response(200, json={
        "items": [{"id": 77, "title": "Logo Tee", "description": "d",
                   "variants": [{"id": 1, "sku": "SKU-1", "d2cPrice": 24.99, "b2bPrice": 11.2}], "images": [{"id": 5, "imageUrl": "https://img.test/1.png"}]}],
        "count": 30, "limit": 10, "offset": 10}))
    res = await _server().call_tool("list_products", {"page": 2, "limit": 10})
    assert res.is_error is False
    p = res.structured_content["products"][0]
    assert p["id"] == "77" and p["sku"] == "SKU-1" and p["price"] == 24.99 and p["image_url"] == "https://img.test/1.png"
    assert res.structured_content["total"] == 30
    req = respx.calls.last.request
    assert req.url.params["limit"] == "10" and req.url.params["offset"] == "10"
    assert req.headers["X-SPOD-ACCESS-TOKEN"] == "tok"


@pytest.mark.asyncio
@respx.mock
async def test_track_lists_shipments_as_events():
    respx.get(f"{BASE}/orders/42/shipments").mock(return_value=httpx.Response(200, json=[
        {"id": 9, "orderId": 42, "shipping": {"type": {"id": "1", "company": "DHL", "name": "Standard"}}, "tracking": [{"code": "JJD01", "url": "https://dhl.test/JJD01"}], "sentDate": "2026-09-20"}]))
    res = await _server().call_tool("track", {"order_id": "42"})
    assert res.is_error is False
    ev = res.structured_content["events"]
    assert ev[0]["tracking_number"] == "JJD01" and ev[0]["carrier"] == "DHL" and ev[0]["shipment_id"] == "9"


@pytest.mark.asyncio
@respx.mock
async def test_get_order_maps_state_and_price_and_bad_token_is_auth_error():
    respx.get(f"{BASE}/orders/42").mock(return_value=httpx.Response(200, json={"id": 42, "orderReference": 1001, "externalOrderReference": "A-1", "state": "CONFIRMED", "price": {"amount": 31.5, "currency": "EUR"}}))
    res = await _server().call_tool("get_order", {"id": "42"})
    assert res.structured_content["status"] == "CONFIRMED" and res.structured_content["total"] == 31.5 and res.structured_content["currency"] == "EUR"
    respx.get(f"{BASE}/authentication").mock(return_value=httpx.Response(401, json={}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
