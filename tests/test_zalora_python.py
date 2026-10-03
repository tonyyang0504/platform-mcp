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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "zalora.json").read_text(encoding="utf-8"))
API = "https://sellercenter-api.zalora.com"
CREDS = {"client_id": "zal-app", "client_secret": "ZALSECRETvalue", "country": "MY"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


def _token():
    return respx.post(f"{API}/oauth/client-credentials").mock(return_value=httpx.Response(200, json={"access_token": "zal.at", "expires_in": 3600, "token_type": "Bearer"}))


@pytest.mark.asyncio
@respx.mock
async def test_basic_client_credentials_and_probe():
    tok = _token()
    respx.get(f"{API}/v2/seller-settings").mock(return_value=httpx.Response(200, json={"sellerId": 1}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["end_listing", "list_orders", "me", "set_inventory", "update_listing"]
    assert (await server.call_tool("me", {})).is_error is False
    req = tok.calls.last.request
    assert req.headers["Authorization"] == "Basic " + base64.b64encode(b"zal-app:ZALSECRETvalue").decode()
    assert parse_qs(req.content.decode()) == {"grant_type": ["client_credentials"]}


@pytest.mark.asyncio
@respx.mock
async def test_price_status_and_stock():
    _token()
    price = respx.put(f"{API}/v2/product/555/prices/MY").mock(return_value=httpx.Response(200, json={"productId": 555, "price": 89.9, "country": "MY", "status": "active"}))
    res = await _server().call_tool("update_listing", {"listing_id": "555", "price": 89.9})
    assert res.structured_content["status"] == "active" and json.loads(price.calls.last.request.content) == {"price": 89.9}
    st = respx.put(f"{API}/v2/product/555/prices/MY/status").mock(return_value=httpx.Response(200, json={"status": "inactive"}))
    await _server().call_tool("end_listing", {"listing_id": "555"})
    assert json.loads(st.calls.last.request.content) == {"status": "inactive"}
    stock = respx.put(f"{API}/v2/stock/product").mock(return_value=httpx.Response(200, json=[{"productId": 555, "quantity": 8}]))
    await _server().call_tool("set_inventory", {"listing_id": "555", "quantity": 8})
    assert json.loads(stock.calls.last.request.content) == [{"productId": 555, "quantity": 8}]


@pytest.mark.asyncio
@respx.mock
async def test_orders_offset_and_section():
    _token()
    route = respx.get(f"{API}/v2/orders").mock(return_value=httpx.Response(200, json={"items": [{"id": 9001, "number": "MY123", "currency": "MYR", "grandTotal": 99.0, "createdAt": "2026-09-20 10:00:00"}]}))
    res = await _server().call_tool("list_orders", {"status": "status_pending", "page": 3, "limit": 20})
    o = res.structured_content["orders"][0]
    assert o["id"] == "9001" and o["total"] == 99.0 and o["currency"] == "MYR"
    p = route.calls.last.request.url.params
    assert p["section"] == "status_pending" and p["offset"] == "40" and p["limit"] == "20" and p["sortDir"] == "desc"
