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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "takealot.json").read_text(encoding="utf-8"))
API = "https://seller-api.takealot.com/v2"
CREDS = {"authorization": "Key TAKEALOT-secret-key-123", "merchant_warehouse_id": "4521"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


@pytest.mark.asyncio
@respx.mock
async def test_me_sends_the_portal_authorization_value():
    route = respx.get(f"{API}/offers/count").mock(return_value=httpx.Response(200, json={"count": 42}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["end_listing", "me", "set_inventory", "update_listing"]
    res = await server.call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["count"] == 42
    assert route.calls.last.request.headers["Authorization"] == "Key TAKEALOT-secret-key-123"


@pytest.mark.asyncio
@respx.mock
async def test_offer_patches():
    route = respx.patch(f"{API}/offers/offer/123456").mock(return_value=httpx.Response(200, json={"offer": {"offer_id": 123456, "status": "Buyable", "selling_price": 499}, "validation_errors": []}))
    res = await _server().call_tool("update_listing", {"listing_id": "123456", "price": 499})
    assert res.is_error is False and res.structured_content["status"] == "Buyable"
    assert json.loads(route.calls.last.request.content) == {"selling_price": 499}
    res = await _server().call_tool("update_listing", {"listing_id": "123456", "price": 499.5})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input"
    await _server().call_tool("end_listing", {"listing_id": "123456"})
    assert json.loads(route.calls.last.request.content) == {"status_action": "Disable"}


@pytest.mark.asyncio
@respx.mock
async def test_set_inventory_targets_sku_identifier_and_warehouse():
    route = respx.patch(f"{API}/offers/offer/SKUDF22").mock(return_value=httpx.Response(200, json={"offer": {"offer_id": 1, "status": "Buyable"}}))
    res = await _server().call_tool("set_inventory", {"sku": "DF22", "quantity": 9})
    assert res.is_error is False
    assert json.loads(route.calls.last.request.content) == {"leadtime_stock": [{"merchant_warehouse_id": 4521, "quantity": 9}]}
