import json
import re
import sys
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "meta_shops.json").read_text(encoding="utf-8"))
API = "https://graph.facebook.com/v25.0"
CREDS = {"access_token": "EAAG-system-user-token", "catalog_id": "111", "cms_id": "222", "currency": "USD"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a["envelope"]))


@pytest.mark.asyncio
@respx.mock
async def test_me_reads_catalog_with_bearer():
    route = respx.get(f"{API}/111").mock(return_value=httpx.Response(200, json={"id": "111", "name": "Main", "product_count": 12}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["end_listing", "list_orders", "mark_shipped", "me", "set_inventory", "update_listing"]
    assert (await server.call_tool("me", {})).structured_content["account"]["product_count"] == 12
    assert route.calls.last.request.headers["Authorization"] == "Bearer EAAG-system-user-token"


@pytest.mark.asyncio
@respx.mock
async def test_items_batch_update_formats_price_with_currency():
    route = respx.post(f"{API}/111/items_batch").mock(return_value=httpx.Response(200, json={"handles": ["h1"], "validation_status": []}))
    res = await _server().call_tool("update_listing", {"listing_id": "SKU-1", "price": 9.99, "quantity": 4})
    assert res.structured_content["status"] == "batch_submitted"
    assert json.loads(route.calls.last.request.content) == {"item_type": "PRODUCT_ITEM", "requests": [{"method": "UPDATE", "data": {"id": "SKU-1", "price": "9.99 USD", "quantity_to_sell_on_facebook": 4}}]}
    await _server().call_tool("end_listing", {"listing_id": "SKU-1"})
    assert json.loads(route.calls.last.request.content) == {"item_type": "PRODUCT_ITEM", "requests": [{"method": "DELETE", "data": {"id": "SKU-1"}}]}


@pytest.mark.asyncio
@respx.mock
async def test_orders_and_shipment():
    orders = respx.get(f"{API}/222/commerce_orders").mock(return_value=httpx.Response(200, json={"data": [{"id": "64000841790004", "order_status": {"state": "IN_PROGRESS"}, "created": "2026-09-20T10:00:00+00:00"}], "paging": {}}))
    res = await _server().call_tool("list_orders", {"status": "IN_PROGRESS"})
    assert res.structured_content["orders"][0]["status"] == "IN_PROGRESS"
    assert orders.calls.last.request.url.params["state"] == "IN_PROGRESS"
    ship = respx.post(f"{API}/64000841790004/shipments").mock(return_value=httpx.Response(200, json={"success": True}))
    res = await _server().call_tool("mark_shipped", {"order_id": "64000841790004", "carrier": "FEDEX", "tracking_number": "ZW923"})
    body = json.loads(ship.calls.last.request.content)
    assert res.is_error is False and body["tracking_info"] == {"carrier": "FEDEX", "tracking_number": "ZW923"}
    assert re.fullmatch(r"[0-9a-f-]{36}", body["idempotency_key"])
