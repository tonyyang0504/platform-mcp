import base64
import json
import re
import sys
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "walmart.json").read_text(encoding="utf-8"))
API = "https://marketplace.walmartapis.com"


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], {"client_id": "CID-wm", "client_secret": "SECRET-wm-1"}, 50, "test")
    t.fixed_headers = a["headers"]
    return build_server(SPEC, transport=t)


def _token_route():
    return respx.post(f"{API}/v3/token").mock(return_value=httpx.Response(200, json={"access_token": "ACCESS-wm", "token_type": "Bearer", "expires_in": 900}))


@pytest.mark.asyncio
async def test_tools():
    assert sorted(t.name for t in await _server().list_tools()) == ["end_listing", "list_orders", "me", "set_inventory", "update_listing"]


@pytest.mark.asyncio
@respx.mock
async def test_token_request_carries_walmart_headers_and_calls_use_wm_sec_token():
    tok = _token_route()
    me = respx.get(f"{API}/v3/token/detail").mock(return_value=httpx.Response(200, json={"is_valid": True, "scopes": {"orders": "full_access"}}))
    server = _server()
    assert (await server.call_tool("me", {})).is_error is False
    assert (await server.call_tool("me", {})).is_error is False
    treq = tok.calls[0].request
    assert treq.headers["Authorization"] == "Basic " + base64.b64encode(b"CID-wm:SECRET-wm-1").decode()
    assert treq.headers["WM_SVC.NAME"] == "Walmart Marketplace" and treq.headers["WM_QOS.CORRELATION_ID"].startswith("platform-mcp-")
    assert treq.content.decode() == "grant_type=client_credentials"
    ids = []
    for call in me.calls:
        h = call.request.headers
        assert h["WM_SEC.ACCESS_TOKEN"] == "ACCESS-wm" and "Authorization" not in h and h["WM_SVC.NAME"] == "Walmart Marketplace"
        assert re.fullmatch(r"[0-9a-f]{32}", h["WM_QOS.CORRELATION_ID"])
        ids.append(h["WM_QOS.CORRELATION_ID"])
    assert len(set(ids)) == 2 and len(tok.calls) == 1


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_maps_purchase_orders():
    _token_route()
    route = respx.get(url__startswith=f"{API}/v3/orders").mock(return_value=httpx.Response(200, json={"list": {"meta": {"totalCount": 31, "limit": 2, "nextCursor": "?limit=2&hasMoreElements=true"}, "elements": {"order": [
        {"purchaseOrderId": "1796277083022", "customerOrderId": "5281956426648", "orderDate": 1568466571000}, {"purchaseOrderId": "3796235970012", "customerOrderId": "5241952426446"}]}}}))
    res = await _server().call_tool("list_orders", {"since": "2026-09-01", "status": "Created", "limit": 2})
    sc = res.structured_content
    assert res.is_error is False and [o["id"] for o in sc["orders"]] == ["1796277083022", "3796235970012"] and sc["total"] == 31
    assert dict(route.calls[0].request.url.params) == {"createdStartDate": "2026-09-01", "status": "Created", "limit": "2"}


@pytest.mark.asyncio
@respx.mock
async def test_update_price_and_inventory_bodies():
    _token_route()
    price = respx.put(f"{API}/v3/price").mock(return_value=httpx.Response(200, json={"ItemPriceResponse": {"mart": "WALMART_US", "message": "The price of the item has been updated.", "sku": "97964_KFTest"}}))
    inv = respx.put(url__startswith=f"{API}/v3/inventory").mock(return_value=httpx.Response(200, json={"sku": "97964_KFTest", "quantity": {"unit": "EACH", "amount": 10}}))
    server = _server()
    res = await server.call_tool("update_listing", {"listing_id": "97964_KFTest", "price": 12.5})
    assert res.is_error is False and res.structured_content["status"] == "price_updated"
    assert json.loads(price.calls[0].request.content) == {"sku": "97964_KFTest", "pricing": [{"currentPriceType": "BASE", "currentPrice": {"currency": "USD", "amount": 12.5}}]}
    assert (await server.call_tool("set_inventory", {"sku": "97964_KFTest", "quantity": 10})).is_error is False
    assert inv.calls[0].request.url.params["sku"] == "97964_KFTest"
    assert json.loads(inv.calls[0].request.content) == {"sku": "97964_KFTest", "quantity": {"unit": "EACH", "amount": 10}}


@pytest.mark.asyncio
@respx.mock
async def test_retire_item_and_400_error():
    _token_route()
    respx.delete(f"{API}/v3/items/SKU-1").mock(return_value=httpx.Response(200, json={"sku": "SKU-1", "message": "Thank you.", "errors": None}))
    respx.delete(f"{API}/v3/items/SKU-2").mock(return_value=httpx.Response(400, json={"errors": [{"code": "INVALID_REQUEST_CONTENT.GMP_ITEM_API"}]}))
    server = _server()
    ok = await server.call_tool("end_listing", {"listing_id": "SKU-1"})
    assert ok.is_error is False and ok.structured_content["status"] == "retire_submitted"
    bad = await server.call_tool("end_listing", {"listing_id": "SKU-2"})
    assert bad.is_error is True and bad.structured_content["error"] == "invalid_input"
