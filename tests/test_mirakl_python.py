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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "mirakl.json").read_text(encoding="utf-8"))
API = "https://market.example.com"
CREDS = {"api_key": "SHOPKEY-0123456789abcdef", "instance_host": "market.example.com", "shop_id": "2001"}


def _server(creds=None):
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], dict(creds or CREDS), 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
@respx.mock
async def test_me_sends_raw_shop_key_to_the_configured_instance():
    route = respx.get(f"{API}/api/account").mock(return_value=httpx.Response(200, json={"shop_id": 2001, "shop_name": "Acme", "currency_iso_code": "EUR"}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["list_orders", "mark_shipped", "me"]
    res = await server.call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["shop_name"] == "Acme"
    req = route.calls.last.request
    assert req.headers["Authorization"] == "SHOPKEY-0123456789abcdef" and req.url.params["shop_id"] == "2001"


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_maps_or11_with_offset_pagination():
    route = respx.get(f"{API}/api/orders").mock(return_value=httpx.Response(200, json={"total_count": 12, "orders": [
        {"order_id": "ORD-1-A", "order_state": "SHIPPING", "total_price": 59.9, "currency_iso_code": "EUR", "created_date": "2026-09-20T10:00:00Z", "shipping_tracking": None}]}))
    res = await _server().call_tool("list_orders", {"status": "SHIPPING", "since": "2026-09-01T00:00:00Z", "page": 2, "limit": 1})
    assert res.is_error is False
    o = res.structured_content["orders"][0]
    assert o["id"] == "ORD-1-A" and o["status"] == "SHIPPING" and o["total"] == 59.9 and o["currency"] == "EUR"
    assert res.structured_content["total"] == 12 and res.structured_content["next_page"] == 3
    p = route.calls.last.request.url.params
    assert p["order_state_codes"] == "SHIPPING" and p["start_date"] == "2026-09-01T00:00:00Z" and p["offset"] == "1" and p["max"] == "1"


@pytest.mark.asyncio
@respx.mock
async def test_mark_shipped_puts_tracking_and_answers_204():
    route = respx.put(f"{API}/api/orders/ORD-1-A/tracking").mock(return_value=httpx.Response(204))
    res = await _server().call_tool("mark_shipped", {"order_id": "ORD-1-A", "carrier": "UPS", "tracking_number": "1Z999"})
    assert res.is_error is False and res.structured_content["status"] == "tracking_updated"
    assert json.loads(route.calls.last.request.content) == {"carrier_code": "UPS", "tracking_number": "1Z999"}


@pytest.mark.asyncio
@respx.mock
async def test_bad_key_is_auth_error_without_secret():
    respx.get(f"{API}/api/account").mock(return_value=httpx.Response(401, json={"message": "Unauthorized key SHOPKEY-0123456789abcdef", "status": 401}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "SHOPKEY-0123456789abcdef" not in json.dumps(res.structured_content)
