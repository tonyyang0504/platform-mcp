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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "kogan.json").read_text(encoding="utf-8"))
API = "https://nimda-marketplace.aws.kgn.io/api/marketplace/v2"
CREDS = {"seller_token": "TOKEN-abcdef123456", "seller_id": "acme", "api_host": "nimda-marketplace.aws.kgn.io"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


@pytest.mark.asyncio
@respx.mock
async def test_me_sends_seller_headers_to_uat_host():
    route = respx.get(f"{API}/products/").mock(return_value=httpx.Response(200, json={"status": "Complete", "body": {"next": None, "previous": None, "results": []}}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["end_listing", "list_orders", "me", "set_inventory", "update_listing"]
    assert (await server.call_tool("me", {})).is_error is False
    req = route.calls.last.request
    assert req.headers["SellerToken"] == "TOKEN-abcdef123456" and req.headers["SellerID"] == "acme" and req.url.params["size"] == "1"


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_maps_body_rows():
    route = respx.get(f"{API}/orders/").mock(return_value=httpx.Response(200, json={"status": "Complete", "body": [
        {"ID": "K-100", "OrderStatus": "ReleasedForShipment", "TotalPrice": 759.99, "Currency": "AUD", "OrderDateUtc": "2026-09-20T01:00:00Z", "Items": []}]}))
    res = await _server().call_tool("list_orders", {"status": "ReleasedForShipment", "since": "2026-09-01T00:00:00Z", "limit": 10})
    o = res.structured_content["orders"][0]
    assert o["id"] == "K-100" and o["status"] == "ReleasedForShipment" and o["total"] == 759.99 and o["currency"] == "AUD"
    p = route.calls.last.request.url.params
    assert p["status"] == "ReleasedForShipment" and p["startDateUTC"] == "2026-09-01T00:00:00Z" and p["limit"] == "10"


@pytest.mark.asyncio
@respx.mock
async def test_writes_send_array_and_object_bodies():
    stock = respx.post(f"{API}/products/stockprice/").mock(return_value=httpx.Response(200, json={"status": "AsyncResponsePending", "pending_url": f"{API}/task/t1/", "body": {}}))
    res = await _server().call_tool("set_inventory", {"sku": "SGS10EWHT128", "quantity": 0})
    assert res.structured_content["status"] == "AsyncResponsePending"
    assert json.loads(stock.calls.last.request.content) == [{"product_sku": "SGS10EWHT128", "stock": 0}]
    patch = respx.patch(f"{API}/products/").mock(return_value=httpx.Response(200, json={"status": "Complete", "body": {"errors": [], "warnings": []}}))
    await _server().call_tool("update_listing", {"listing_id": "SGS10EWHT128", "title": "Samsung Galaxy S10e White 128GB"})
    assert json.loads(patch.calls.last.request.content) == [{"product_sku": "SGS10EWHT128", "product_title": "Samsung Galaxy S10e White 128GB"}]
    status = respx.post(f"{API}/products/status/").mock(return_value=httpx.Response(200, json={"status": "Complete", "body": {"errors": [], "warnings": []}}))
    await _server().call_tool("end_listing", {"listing_id": "SGS10EWHT128"})
    assert json.loads(status.calls.last.request.content) == {"product_sku": "SGS10EWHT128", "enabled": False}


@pytest.mark.asyncio
@respx.mock
async def test_forbidden_is_auth_error_without_token():
    respx.post(f"{API}/products/status/").mock(return_value=httpx.Response(403, json={"detail": "no permission for TOKEN-abcdef123456"}))
    res = await _server().call_tool("end_listing", {"listing_id": "X"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "TOKEN-abcdef123456" not in json.dumps(res.structured_content)
