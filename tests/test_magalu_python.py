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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "magalu.json").read_text(encoding="utf-8"))
TOKEN_URL = "https://id.magalu.com/oauth/token"
API = "https://api.magalu.com/seller/v1"
CREDS = {"client_id": "mg-client", "client_secret": "MGSECRETvalue", "refresh_token": "RT-magalu-1", "channel_id": "ch-1"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


def _token():
    return respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "eyJ.acc", "token_type": "Bearer", "expires_in": 7200, "refresh_token": "RT-magalu-2"}))


@pytest.mark.asyncio
@respx.mock
async def test_refresh_form_and_me():
    tok = _token()
    respx.get(f"{API}/portfolios/me").mock(return_value=httpx.Response(200, json={"tenant": {"id": "t"}, "channel": {"id": "ch-1"}, "seller": {"id": "s", "name": "Loja"}}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["end_listing", "list_orders", "me", "set_inventory"]
    res = await server.call_tool("me", {})
    assert res.structured_content["account"]["seller"]["name"] == "Loja"
    assert parse_qs(tok.calls.last.request.content.decode()) == {"grant_type": ["refresh_token"], "refresh_token": ["RT-magalu-1"], "client_id": ["mg-client"], "client_secret": ["MGSECRETvalue"]}


@pytest.mark.asyncio
@respx.mock
async def test_stock_and_deactivate():
    _token()
    stock = respx.patch(f"{API}/portfolios/stocks/SKU-1").mock(return_value=httpx.Response(202, json={"trace_id": "tr-1"}))
    res = await _server().call_tool("set_inventory", {"sku": "SKU-1", "quantity": 7})
    assert res.structured_content["status"] == "accepted"
    assert json.loads(stock.calls.last.request.content) == {"channel": {"id": "ch-1"}, "type": "AVAILABLE", "quantity": 7}
    sku = respx.patch(f"{API}/portfolios/skus/SKU-1").mock(return_value=httpx.Response(202, json={"trace_id": "tr-2"}))
    await _server().call_tool("end_listing", {"listing_id": "SKU-1"})
    assert json.loads(sku.calls.last.request.content) == {"active": False}


@pytest.mark.asyncio
@respx.mock
async def test_orders_offset_paging():
    _token()
    route = respx.get(f"{API}/orders").mock(return_value=httpx.Response(200, json={"meta": {"links": {"self": "x"}, "page": {"count": 45, "limit": 20, "max_limit": 100, "offset": 20}},
        "results": [{"code": "LU-1", "status": "approved", "purchased_at": "2026-09-20T10:00:00-03:00", "amounts": {"currency": "BRL", "total": 1999, "normalizer": 100}}]}))
    res = await _server().call_tool("list_orders", {"status": "approved", "page": 2})
    o = res.structured_content["orders"][0]
    assert o["id"] == "LU-1" and o["currency"] == "BRL" and res.structured_content["total"] == 45
    p = route.calls.last.request.url.params
    assert p["_offset"] == "20" and p["_limit"] == "20" and p["status"] == "approved" and p["_sort"] == "purchased_at:desc"
