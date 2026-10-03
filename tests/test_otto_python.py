import json
import sys
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "otto.json").read_text(encoding="utf-8"))
API = "https://api.otto.market"
CREDS = {"client_id": "otto-app", "client_secret": "OTTOSECRETvalue", "currency": "EUR"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


def _token():
    return respx.post(f"{API}/v1/token").mock(return_value=httpx.Response(200, json={"access_token": "otto.jwt", "expires_in": 1800, "token_type": "Bearer"}))


@pytest.mark.asyncio
@respx.mock
async def test_client_credentials_with_scopes():
    tok = _token()
    route = respx.get(f"{API}/v1/availability/quantities").mock(return_value=httpx.Response(200, json={"resources": {"variations": []}, "links": []}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["end_listing", "list_orders", "me", "set_inventory", "update_listing"]
    assert (await server.call_tool("me", {})).is_error is False
    form = parse_qs(tok.calls.last.request.content.decode())
    assert form["grant_type"] == ["client_credentials"] and form["scope"] == ["products availability orders shipments"] and form["client_id"] == ["otto-app"]
    assert route.calls.last.request.headers["Authorization"] == "Bearer otto.jwt"


@pytest.mark.asyncio
@respx.mock
async def test_price_quantity_and_offline_bodies():
    _token()
    price = respx.post(f"{API}/v5/products/prices").mock(return_value=httpx.Response(202, json={"state": "pending", "links": []}))
    res = await _server().call_tool("update_listing", {"listing_id": "SKU-1", "price": 49.95})
    assert res.structured_content["status"] == "pending"
    assert json.loads(price.calls.last.request.content) == [{"sku": "SKU-1", "standardPrice": {"amount": 49.95, "currency": "EUR"}}]
    qty = respx.post(f"{API}/v1/availability/quantities").mock(return_value=httpx.Response(207, json={"results": [{"sku": "SKU-1", "quantity": 3}], "errors": []}))
    await _server().call_tool("set_inventory", {"sku": "SKU-1", "quantity": 3})
    assert json.loads(qty.calls.last.request.content) == [{"sku": "SKU-1", "quantity": 3}]
    act = respx.post(f"{API}/v5/products/active-status").mock(return_value=httpx.Response(202, json={"state": "pending"}))
    await _server().call_tool("end_listing", {"listing_id": "SKU-1"})
    assert json.loads(act.calls.last.request.content) == {"status": [{"sku": "SKU-1", "active": False}]}


@pytest.mark.asyncio
@respx.mock
async def test_orders():
    _token()
    route = respx.get(f"{API}/v4/orders").mock(return_value=httpx.Response(200, json={"resources": [
        {"orderNumber": "bu5h6x7z", "salesOrderId": "4a1c", "orderDate": "2026-09-20T10:00:00Z", "positionItems": [{"fulfillmentStatus": "PROCESSABLE", "itemValueGrossPrice": {"amount": 49.95, "currency": "EUR"}}]}], "links": []}))
    res = await _server().call_tool("list_orders", {"status": "PROCESSABLE", "since": "2026-09-01T00:00:00Z"})
    o = res.structured_content["orders"][0]
    assert o["id"] == "bu5h6x7z" and o["status"] == "PROCESSABLE" and o["currency"] == "EUR"
    p = route.calls.last.request.url.params
    assert p["fulfillmentStatus"] == "PROCESSABLE" and p["fromOrderDate"] == "2026-09-01T00:00:00Z"
