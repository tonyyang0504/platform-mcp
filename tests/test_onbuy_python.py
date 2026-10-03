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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "onbuy.json").read_text(encoding="utf-8"))
API = "https://api.onbuy.com/v2"
CREDS = {"consumer_key": "ck_live_123456", "secret_key": "sk_live_abcdef", "site_id": "2000"}
TOKEN = {"access_token": "4E7DREERR2189-A943-4697-C295-fCA434558518", "expires_at": 1514764800}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


@pytest.mark.asyncio
@respx.mock
async def test_form_login_then_raw_authorization_header():
    login = respx.post(f"{API}/auth/request-token").mock(return_value=httpx.Response(200, json=TOKEN))
    site = respx.get(f"{API}/sites/2000").mock(return_value=httpx.Response(200, json={"results": {"site_id": 2000, "name": "OnBuy UK"}}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["end_listing", "list_orders", "mark_shipped", "me", "set_inventory", "update_listing"]
    assert (await server.call_tool("me", {})).is_error is False
    assert parse_qs(login.calls.last.request.content.decode()) == {"secret_key": ["sk_live_abcdef"], "consumer_key": ["ck_live_123456"]}
    assert site.calls.last.request.headers["Authorization"] == TOKEN["access_token"]


@pytest.mark.asyncio
@respx.mock
async def test_listing_writes_by_sku():
    respx.post(f"{API}/auth/request-token").mock(return_value=httpx.Response(200, json=TOKEN))
    put = respx.put(f"{API}/listings/by-sku").mock(return_value=httpx.Response(200, json={"success": True, "results": [{"sku": "EXP-143-33S", "price": "14.83", "stock": 88}]}))
    res = await _server().call_tool("update_listing", {"listing_id": "EXP-143-33S", "price": 14.83, "quantity": 88})
    assert res.is_error is False and res.structured_content["status"] == "updated"
    assert json.loads(put.calls.last.request.content) == {"site_id": 2000, "listings": [{"sku": "EXP-143-33S", "price": 14.83, "stock": 88}]}
    delete = respx.delete(f"{API}/listings/by-sku").mock(return_value=httpx.Response(200, json={"success": True, "results": {"EXP-143-33S": {"status": "ok"}}}))
    await _server().call_tool("end_listing", {"listing_id": "EXP-143-33S"})
    assert json.loads(delete.calls.last.request.content) == {"site_id": 2000, "skus": ["EXP-143-33S"]}


@pytest.mark.asyncio
@respx.mock
async def test_orders_browse_and_dispatch():
    respx.post(f"{API}/auth/request-token").mock(return_value=httpx.Response(200, json=TOKEN))
    route = respx.get(f"{API}/orders").mock(return_value=httpx.Response(200, json={"results": [
        {"order_id": "TNQ2K", "status": "Awaiting Dispatch", "price_total": "899.98", "currency_code": "GBP", "date": "2026-09-12 09:22:09"}]}))
    res = await _server().call_tool("list_orders", {"status": "awaiting_dispatch", "since": "2026-09-01 00:00:00"})
    o = res.structured_content["orders"][0]
    assert o["id"] == "TNQ2K" and o["total"] == "899.98" and o["currency"] == "GBP"
    p = route.calls.last.request.url.params
    assert p["filter[status]"] == "awaiting_dispatch" and p["filter[date_from]"] == "2026-09-01 00:00:00" and p["site_id"] == "2000"
    ship = respx.put(f"{API}/orders/dispatch").mock(return_value=httpx.Response(200, json={"success": True, "results": {"TNQ2K": {"success": True}}}))
    res = await _server().call_tool("mark_shipped", {"order_id": "TNQ2K", "carrier": "Royal Mail", "tracking_number": "CP845505093GB"})
    assert json.loads(ship.calls.last.request.content) == {"site_id": 2000, "orders": [{"order_id": "TNQ2K", "tracking": {"supplier_name": "Royal Mail", "number": "CP845505093GB"}}]}


@pytest.mark.asyncio
@respx.mock
async def test_expired_token_relogs_once():
    login = respx.post(f"{API}/auth/request-token").mock(side_effect=[httpx.Response(200, json=TOKEN), httpx.Response(200, json={"access_token": "NEWTOKEN-0000000000", "expires_at": 1})])
    respx.get(f"{API}/orders").mock(side_effect=[httpx.Response(401, json={"error": "expired"}), httpx.Response(200, json={"results": []})])
    res = await _server().call_tool("list_orders", {})
    assert res.is_error is False and len(login.calls) == 2
