import base64
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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "trendyol.json").read_text(encoding="utf-8"))
API = "https://stageapigw.trendyol.com/integration"
CREDS = {"api_key": "TYKEY123456", "api_secret": "TYSECRET987654", "seller_id": "1234", "user_agent": "1234 - SelfIntegration", "api_host": "stageapigw.trendyol.com"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


@pytest.mark.asyncio
@respx.mock
async def test_me_uses_basic_auth_and_mandatory_user_agent():
    route = respx.get(f"{API}/sellers/1234/addresses").mock(return_value=httpx.Response(200, json={"supplierAddresses": [{"id": 1, "addressType": "Shipment"}]}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["end_listing", "list_orders", "me", "set_inventory", "update_listing"]
    assert (await server.call_tool("me", {})).is_error is False
    h = route.calls.last.request.headers
    assert h["Authorization"] == "Basic " + base64.b64encode(b"TYKEY123456:TYSECRET987654").decode() and h["User-Agent"] == "1234 - SelfIntegration"


@pytest.mark.asyncio
@respx.mock
async def test_price_stock_and_archive_bodies():
    inv = respx.post(f"{API}/inventory/sellers/1234/products/price-and-inventory").mock(return_value=httpx.Response(200, json={"batchRequestId": "fa75dfd5"}))
    res = await _server().call_tool("update_listing", {"listing_id": "8680000000", "price": 112.85, "quantity": 100})
    assert res.structured_content["status"] == "batch_submitted"
    assert json.loads(inv.calls.last.request.content) == {"items": [{"barcode": "8680000000", "salePrice": 112.85, "listPrice": 112.85, "quantity": 100}]}
    await _server().call_tool("set_inventory", {"sku": "8680000000", "quantity": 5})
    assert json.loads(inv.calls.last.request.content) == {"items": [{"barcode": "8680000000", "quantity": 5}]}
    arch = respx.put(f"{API}/product/sellers/1234/products/archive-state").mock(return_value=httpx.Response(200, json={"batchRequestId": "b2"}))
    await _server().call_tool("end_listing", {"listing_id": "8680000000"})
    assert json.loads(arch.calls.last.request.content) == {"items": [{"barcode": "8680000000", "archived": True}]}


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_v2_zero_based_pages():
    route = respx.get(f"{API}/order/sellers/1234/v2/orders").mock(return_value=httpx.Response(200, json={"totalElements": 3, "totalPages": 3, "page": 1, "size": 1, "content": [
        {"id": 11650604, "orderNumber": "10654411111", "status": "Created", "packageTotalPrice": 498.9, "currencyCode": "TRY", "orderDate": 1762253333685, "cargoTrackingNumber": 7280027504111111}]}))
    res = await _server().call_tool("list_orders", {"status": "Created", "page": 2, "limit": 1})
    o = res.structured_content["orders"][0]
    assert o["id"] == "10654411111" and o["total"] == 498.9 and o["currency"] == "TRY" and res.structured_content["total"] == 3 and res.structured_content["next_page"] == 3
    p = route.calls.last.request.url.params
    assert p["page"] == "1" and p["size"] == "1" and p["status"] == "Created" and p["orderByField"] == "PackageLastModifiedDate"


@pytest.mark.asyncio
@respx.mock
async def test_missing_user_agent_403_is_auth_error():
    respx.get(f"{API}/sellers/1234/addresses").mock(return_value=httpx.Response(403, json={"exception": "ClientApiAuthenticationException"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
