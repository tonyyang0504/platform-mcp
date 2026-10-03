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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "manomano.json").read_text(encoding="utf-8"))
API = "https://partnersapi.manomano.com"
CREDS = {"api_key": "MMKEY-u4EAhgExMQSu", "seller_contract_id": "110841"}


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test")
    t.fixed_headers = a["headers"]
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
@respx.mock
async def test_me_sends_api_key_and_thirdparty_header():
    route = respx.get(f"{API}/api/v1/offer-information/offers").mock(return_value=httpx.Response(200, json={"pagination": {"page": 1, "limit": 1}, "content": []}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["list_orders", "mark_shipped", "me", "set_inventory", "update_listing"]
    assert (await server.call_tool("me", {})).is_error is False
    req = route.calls.last.request
    assert req.headers["x-api-key"] == "MMKEY-u4EAhgExMQSu" and req.headers["x-thirdparty-name"] == "platform-mcp_0.1.0"
    assert req.url.params["seller_contract_id"] == "110841"


@pytest.mark.asyncio
@respx.mock
async def test_update_listing_builds_contract_items_body():
    route = respx.patch(f"{API}/api/v2/offer-information/offers").mock(return_value=httpx.Response(200, json={"request_id": "r-1"}))
    res = await _server().call_tool("update_listing", {"listing_id": "ABC-24345", "price": 83.5, "quantity": 250})
    assert res.is_error is False and res.structured_content["status"] == "accepted"
    assert json.loads(route.calls.last.request.content) == {"content": [{"seller_contract_id": 110841, "items": [{"sku": "ABC-24345", "price": {"price_vat_included": 83.5}, "stock": {"quantity": 250}}]}]}
    await _server().call_tool("set_inventory", {"sku": "ABC-24345", "quantity": 0})
    assert json.loads(route.calls.last.request.content) == {"content": [{"seller_contract_id": 110841, "items": [{"sku": "ABC-24345", "stock": {"quantity": 0}}]}]}


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_and_mark_shipped():
    route = respx.get(f"{API}/orders/v1/orders").mock(return_value=httpx.Response(200, json={"content": [
        {"order_reference": "M2022080713464", "status": "PREPARATION", "total_price": {"amount": 166.56, "currency": "EUR"}, "created_at": "2026-09-20T10:00:00Z"}],
        "pagination": {"items": 1, "limit": 30, "page": 1, "pages": 1}}))
    res = await _server().call_tool("list_orders", {"status": "PREPARATION"})
    o = res.structured_content["orders"][0]
    assert o["id"] == "M2022080713464" and o["total"] == 166.56 and o["currency"] == "EUR" and res.structured_content["total"] == 1
    assert route.calls.last.request.url.params["status"] == "PREPARATION"
    ship = respx.post(f"{API}/orders/v1/shippings").mock(return_value=httpx.Response(204))
    res = await _server().call_tool("mark_shipped", {"order_id": "M2022080713464", "carrier": "UPS", "tracking_number": "1Z1594AB5789012374"})
    assert res.is_error is False and res.structured_content["status"] == "shipped"
    assert json.loads(ship.calls.last.request.content) == [{"order_reference": "M2022080713464", "seller_contract_id": 110841, "carrier": "UPS", "tracking_number": "1Z1594AB5789012374"}]


@pytest.mark.asyncio
@respx.mock
async def test_quota_is_rate_limited():
    respx.get(f"{API}/orders/v1/orders").mock(return_value=httpx.Response(429, headers={"Retry-After": "60"}, json={"message": "Too many requests"}))
    res = await _server().call_tool("list_orders", {})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited"
