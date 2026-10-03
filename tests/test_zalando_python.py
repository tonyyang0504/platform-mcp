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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "zalando.json").read_text(encoding="utf-8"))
API = "https://api.merchants.zalando.com"
MID = "8a6d0e3c-0000-4000-8000-000000000001"
SC = "01924c48-49bb-40c2-9c32-ab582e6db6f4"
CREDS = {"client_id": "zd-client", "client_secret": "ZDSECRETvalue", "merchant_id": MID, "sales_channel_id": SC, "currency": "EUR"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


def _token():
    return respx.post(f"{API}/auth/token").mock(return_value=httpx.Response(200, json={"access_token": "zd.jwt", "token_type": "Bearer", "expires_in": 7200}))


@pytest.mark.asyncio
@respx.mock
async def test_basic_token_with_scope_and_me():
    tok = _token()
    respx.get(f"{API}/auth/me").mock(return_value=httpx.Response(200, json={"bpids": [MID], "scopes": ["stocks/write"]}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["end_listing", "list_orders", "mark_shipped", "me", "set_inventory", "update_listing"]
    assert (await server.call_tool("me", {})).is_error is False
    req = tok.calls.last.request
    assert req.headers["Authorization"] == "Basic " + base64.b64encode(b"zd-client:ZDSECRETvalue").decode()
    assert parse_qs(req.content.decode()) == {"grant_type": ["client_credentials"], "scope": ["access_token_only"]}


@pytest.mark.asyncio
@respx.mock
async def test_price_stock_and_blocker_bodies():
    _token()
    prices = respx.post(f"{API}/merchants/{MID}/prices").mock(return_value=httpx.Response(207, json={"results": [{"status": "ACCEPTED", "code": 0}]}))
    res = await _server().call_tool("update_listing", {"listing_id": "4062742000123", "price": 59.95})
    assert res.structured_content["status"] == "ACCEPTED"
    assert json.loads(prices.calls.last.request.content) == {"product_prices": [{"ean": "4062742000123", "sales_channel_id": SC, "regular_price": {"amount": 59.95, "currency": "EUR"}}]}
    stocks = respx.post(f"{API}/merchants/{MID}/stocks").mock(return_value=httpx.Response(207, json={"results": [{"item": {}, "result": {"status": "ACCEPTED", "code": 0}}]}))
    res = await _server().call_tool("set_inventory", {"sku": "4062742000123", "quantity": 4})
    assert res.structured_content["status"] == "ACCEPTED"
    assert json.loads(stocks.calls.last.request.content) == {"items": [{"sales_channel_id": SC, "ean": "4062742000123", "quantity": 4}]}
    blk = respx.post(f"{API}/merchants/{MID}/offer-blockers").mock(return_value=httpx.Response(207, json={"results": [{"item": {}, "result": {"status": "ACCEPTED"}}]}))
    await _server().call_tool("end_listing", {"listing_id": "4062742000123"})
    body = json.loads(blk.calls.last.request.content)["items"][0]
    assert body["reason"] == "PAUSE_06" and body["criteria"] == {"sales_channel_id": SC, "ean": "4062742000123"}


@pytest.mark.asyncio
@respx.mock
async def test_jsonapi_orders_and_tracking_patch():
    _token()
    route = respx.get(f"{API}/merchants/{MID}/orders").mock(return_value=httpx.Response(200, headers={"Content-Type": "application/vnd.api+json"}, json={"data": [
        {"type": "Order", "id": "o-uuid-1", "attributes": {"order_number": "10101010", "status": "approved", "order_date": "2026-09-20T10:00:00Z", "order_lines_price_amount": 59.95, "order_lines_price_currency": "EUR"}}]}))
    res = await _server().call_tool("list_orders", {"status": "approved", "page": 1, "limit": 10})
    o = res.structured_content["orders"][0]
    assert o["id"] == "o-uuid-1" and o["status"] == "approved" and o["total"] == 59.95
    req = route.calls.last.request
    assert req.headers["Accept"] == "application/vnd.api+json" and req.url.params["page[size]"] == "10" and req.url.params["sales_channel_id"] == SC
    patch = respx.patch(f"{API}/merchants/{MID}/orders/o-uuid-1").mock(return_value=httpx.Response(204))
    res = await _server().call_tool("mark_shipped", {"order_id": "o-uuid-1", "tracking_number": "00340434"})
    assert res.structured_content["status"] == "tracking_updated"
    preq = patch.calls.last.request
    assert preq.headers["Content-Type"] == "application/vnd.api+json"
    assert json.loads(preq.content) == {"data": {"type": "Order", "id": "o-uuid-1", "attributes": {"tracking_number": "00340434"}}}
