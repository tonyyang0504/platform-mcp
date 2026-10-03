import base64
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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "bol_com.json").read_text(encoding="utf-8"))
TOKEN_URL = "https://login.bol.com/token"
API = "https://api.bol.com/retailer"
VND = "application/vnd.retailer.v10+json"
CREDS = {"client_id": "bol-client-1", "client_secret": "BOLSECRETvalue"}
PS = {"processStatusId": "1234", "eventType": "UPDATE_OFFER_STOCK", "description": "x", "status": "PENDING", "createTimestamp": "2026-09-25T10:00:00+02:00", "links": []}


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test")
    t.fixed_headers = a["headers"]
    return build_server(SPEC, transport=t)


def _token():
    return respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "JWT-abc.def.ghi", "token_type": "Bearer", "expires_in": 299}))


@pytest.mark.asyncio
@respx.mock
async def test_client_credentials_and_vendor_accept():
    tok = _token()
    route = respx.get(f"{API}/orders").mock(return_value=httpx.Response(200, json={"orders": []}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["end_listing", "list_orders", "mark_shipped", "me", "set_inventory", "update_listing"]
    assert (await server.call_tool("me", {})).is_error is False
    treq = tok.calls.last.request
    assert treq.headers["Authorization"] == "Basic " + base64.b64encode(b"bol-client-1:BOLSECRETvalue").decode()
    assert parse_qs(treq.content.decode())["grant_type"] == ["client_credentials"]
    h = route.calls.last.request.headers
    assert h["Authorization"] == "Bearer JWT-abc.def.ghi" and h["Accept"] == VND


@pytest.mark.asyncio
@respx.mock
async def test_offer_writes_use_vendor_content_type():
    _token()
    stock = respx.put(f"{API}/offers/off-1/stock").mock(return_value=httpx.Response(202, json=PS))
    res = await _server().call_tool("set_inventory", {"listing_id": "off-1", "quantity": 12})
    assert res.is_error is False and res.structured_content["status"] == "PENDING"
    req = stock.calls.last.request
    assert req.headers["Content-Type"] == VND and json.loads(req.content) == {"amount": 12, "managedByRetailer": False}
    price = respx.put(f"{API}/offers/off-1/price").mock(return_value=httpx.Response(202, json=PS))
    await _server().call_tool("update_listing", {"listing_id": "off-1", "price": 19.99})
    assert json.loads(price.calls.last.request.content) == {"pricing": {"bundlePrices": [{"quantity": 1, "unitPrice": 19.99}]}}
    dele = respx.delete(f"{API}/offers/off-1").mock(return_value=httpx.Response(202, json=PS))
    assert (await _server().call_tool("end_listing", {"listing_id": "off-1"})).is_error is False and dele.called


@pytest.mark.asyncio
@respx.mock
async def test_orders_and_item_shipment():
    _token()
    route = respx.get(f"{API}/orders").mock(return_value=httpx.Response(200, json={"orders": [
        {"orderId": "1043946570", "orderPlacedDateTime": "2026-09-20T10:00:00+02:00", "orderItems": [{"orderItemId": "6107434013", "fulfilmentStatus": "OPEN"}]}]}))
    res = await _server().call_tool("list_orders", {"status": "OPEN"})
    o = res.structured_content["orders"][0]
    assert o["id"] == "1043946570" and o["status"] == "OPEN"
    p = route.calls.last.request.url.params
    assert p["fulfilment-method"] == "FBR" and p["status"] == "OPEN" and p["page"] == "1"
    ship = respx.post(f"{API}/shipments").mock(return_value=httpx.Response(202, json=PS))
    await _server().call_tool("mark_shipped", {"order_id": "6107434013", "carrier": "TNT", "tracking_number": "3SBOL0987654321"})
    assert json.loads(ship.calls.last.request.content) == {"orderItems": [{"orderItemId": "6107434013"}], "transport": {"transporterCode": "TNT", "trackAndTrace": "3SBOL0987654321"}}
