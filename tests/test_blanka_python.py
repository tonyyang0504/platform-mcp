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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "blanka.json").read_text(encoding="utf-8"))
BASE = "https://api.blankabrand.com/api/v1"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {"api_key": "blk_live_key"}, 50, "test"))


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary():
    tools = {t.name: t for t in await _server().list_tools()}
    assert sorted(tools) == ["create_order", "list_products", "me"]
    assert tools["create_order"].annotations.destructive_hint is True


@pytest.mark.asyncio
@respx.mock
async def test_list_products_pages_and_sends_the_key():
    route = respx.get(f"{BASE}/products/").mock(return_value=httpx.Response(200, json={"count": 450, "next": "http://api.blankabrand.com/api/v1/products/?page=2", "previous": None,
        "results": [{"id": 209567, "name": "Reusable Bamboo Cotton Rounds", "sku": "BLNK-AB-04-02-CTP", "cost": "9.63", "suggested_cost": "18.00", "image": "https://images.blankabrand.com/x.webp"}]}))
    res = await _server().call_tool("list_products", {"page": 1, "limit": 1})
    assert res.is_error is False
    sc = res.structured_content
    p = sc["products"][0]
    assert p["id"] == "209567" and p["sku"] == "BLNK-AB-04-02-CTP" and p["cost"] == "9.63" and sc["total"] == 450 and sc["next_page"] == 2
    req = route.calls.last.request
    assert req.url.params["page"] == "1" and req.url.params["page_size"] == "1"
    assert req.headers["Authorization"] == "blk_live_key"


@pytest.mark.asyncio
@respx.mock
async def test_create_order_sends_line_items_and_address():
    route = respx.post(f"{BASE}/orders/").mock(return_value=httpx.Response(201, json={"id": "337539", "order_id": "x", "status": "PAYMENT_REQUIRED", "tracking_code": None}))
    addr = {"first_name": "John", "last_name": "Smith", "address_1": "16 rodeo drive", "city": "Los Angeles", "state": "California", "postcode": "90210", "country": "US"}
    res = await _server().call_tool("create_order", {"items": [{"sku": "BLNK-AB-04-02-RO-QZ1", "quantity": 2}], "shipping_address": addr})
    assert res.is_error is False and res.structured_content["id"] == "337539" and res.structured_content["status"] == "PAYMENT_REQUIRED"
    body = json.loads(route.calls.last.request.content)
    assert body["line_items"] == [{"sku": "BLNK-AB-04-02-RO-QZ1", "quantity": 2}] and body["shipping_address"] == addr
    assert len(body["order_id"]) == 36


@pytest.mark.asyncio
@respx.mock
async def test_unauthorized_is_an_auth_error_without_the_key():
    respx.get(f"{BASE}/products/").mock(return_value=httpx.Response(401, json={"detail": "Invalid token blk_live_key"}))
    res = await _server().call_tool("list_products", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "blk_live_key" not in json.dumps(res.structured_content)
