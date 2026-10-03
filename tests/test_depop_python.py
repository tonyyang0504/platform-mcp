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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "depop.json").read_text(encoding="utf-8"))
API = "https://partnerapi-staging.depop.com/api/v1"
CREDS = {"api_key": "DEPOP-apikey-secret", "api_host": "partnerapi-staging.depop.com"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


@pytest.mark.asyncio
@respx.mock
async def test_me_bearer():
    route = respx.get(f"{API}/shop/").mock(return_value=httpx.Response(200, json={"id": 123, "username": "shop", "country_code": "GB"}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["end_listing", "list_orders", "me", "set_inventory", "update_listing"]
    res = await server.call_tool("me", {})
    assert res.structured_content["account"]["username"] == "shop"
    assert route.calls.last.request.headers["Authorization"] == "Bearer DEPOP-apikey-secret"


@pytest.mark.asyncio
@respx.mock
async def test_patch_and_delete_by_sku():
    patch = respx.patch(f"{API}/products/by-sku/SKU-9/").mock(return_value=httpx.Response(204))
    res = await _server().call_tool("update_listing", {"listing_id": "SKU-9", "price": 24.5, "quantity": 2})
    assert res.is_error is False and res.structured_content["status"] == "updated"
    assert json.loads(patch.calls.last.request.content) == {"price_amount": "24.5", "quantity": 2}
    await _server().call_tool("set_inventory", {"sku": "SKU-9", "quantity": 0})
    assert json.loads(patch.calls.last.request.content) == {"quantity": 0}
    dele = respx.delete(f"{API}/products/by-sku/SKU-9/").mock(return_value=httpx.Response(204))
    assert (await _server().call_tool("end_listing", {"listing_id": "SKU-9"})).is_error is False and dele.called


@pytest.mark.asyncio
@respx.mock
async def test_orders():
    route = respx.get(f"{API}/orders/").mock(return_value=httpx.Response(200, json={"meta": {"cursor": "p1", "has_more": False}, "data": [
        {"purchase_id": "p1", "status": "SHIPPING_PENDING", "currency": "GBP", "buyer_pays_amount": "27.99", "created_at": "2026-09-20T10:00:00Z", "line_items": []}]}))
    res = await _server().call_tool("list_orders", {"since": "2026-09-01T00:00:00Z", "limit": 50})
    o = res.structured_content["orders"][0]
    assert o["id"] == "p1" and o["total"] == "27.99" and o["status"] == "SHIPPING_PENDING"
    p = route.calls.last.request.url.params
    assert p["from"] == "2026-09-01T00:00:00Z" and p["limit"] == "50"
