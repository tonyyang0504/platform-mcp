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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "stockx.json").read_text(encoding="utf-8"))
API = "https://api.stockx.com/v2"
TOKEN = "https://accounts.stockx.com/oauth/token"
CREDS = {"api_key": "sx_key_5521", "client_id": "sx_cid", "client_secret": "sx_secret_77", "refresh_token": "sx_rt_GEbRxBN", "currency": "EUR"}


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test")
    t.fixed_headers = a["headers"]
    return build_server(SPEC, transport=t)


def _token():
    return respx.post(TOKEN).mock(return_value=httpx.Response(200, json={"access_token": "sx_at_ey", "expires_in": 43200, "token_type": "Bearer"}))


@pytest.mark.asyncio
@respx.mock
async def test_refresh_grant_audience_and_api_key_header():
    tok = _token()
    route = respx.get(f"{API}/selling/listings").mock(return_value=httpx.Response(200, json={"count": 0, "listings": []}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["end_listing", "list_orders", "me", "update_listing"]
    assert (await server.call_tool("me", {})).is_error is False
    form = parse_qs(tok.calls.last.request.content.decode())
    assert form == {"grant_type": ["refresh_token"], "refresh_token": ["sx_rt_GEbRxBN"], "audience": ["gateway.stockx.com"], "client_id": ["sx_cid"], "client_secret": ["sx_secret_77"]}
    h = route.calls.last.request.headers
    assert h["Authorization"] == "Bearer sx_at_ey" and h["x-api-key"] == "sx_key_5521"
    assert route.calls.last.request.url.params["pageSize"] == "1"


@pytest.mark.asyncio
@respx.mock
async def test_active_orders():
    _token()
    route = respx.get(f"{API}/selling/orders/active").mock(return_value=httpx.Response(200, json={"count": 1, "pageSize": 10, "pageNumber": 1, "hasNextPage": False, "orders": [
        {"orderNumber": "323314425-323214184", "status": "CREATED", "amount": "150", "currencyCode": "EUR", "createdAt": "2026-09-20T13:51:47.000Z"}]}))
    res = await _server().call_tool("list_orders", {"status": "CREATED", "limit": 10})
    o = res.structured_content["orders"][0]
    assert o["id"] == "323314425-323214184" and o["currency"] == "EUR" and res.structured_content["total"] == 1
    p = route.calls.last.request.url.params
    assert p["orderStatus"] == "CREATED" and p["pageSize"] == "10" and p["pageNumber"] == "1"


@pytest.mark.asyncio
@respx.mock
async def test_reprice_and_deactivate():
    _token()
    patch = respx.patch(f"{API}/selling/listings/L-1").mock(return_value=httpx.Response(200, json={"listingId": "L-1", "operationId": "op1", "operationStatus": "PENDING"}))
    res = await _server().call_tool("update_listing", {"listing_id": "L-1", "price": 175.5, "title": "ignored"})
    assert res.structured_content["status"] == "PENDING"
    assert json.loads(patch.calls.last.request.content) == {"amount": "175.5", "currencyCode": "EUR"}
    respx.put(f"{API}/selling/listings/L-1/deactivate").mock(return_value=httpx.Response(200, json={"listingId": "L-1", "operationStatus": "PENDING"}))
    assert (await _server().call_tool("end_listing", {"listing_id": "L-1"})).structured_content["status"] == "PENDING"
