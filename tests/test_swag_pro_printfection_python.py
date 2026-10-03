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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "swag_pro_printfection.json").read_text(encoding="utf-8"))
BASE = "https://api.printfection.com/v2"


def _server(creds=None):
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], creds or {"api_key": "pf-secret"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["create_order", "get_order", "get_product", "list_products", "me", "track"]
    co = next(t for t in tools if t.name == "create_order")
    assert co.annotations.destructive_hint is True and co.meta["platform_mcp/endpoint"] == "/orders"


@pytest.mark.asyncio
@respx.mock
async def test_list_items_uses_limit_offset_and_basic_key_as_username():
    respx.get(f"{BASE}/items").mock(return_value=httpx.Response(200, json=[
        {"id": 2, "object": "item", "name": "Amazing Water Bottle", "color": "Clear", "product": {"id": 124, "name": "32oz Nalgene Water Bottle"},
         "created_at": "2014-09-12T10:22:37Z", "campaigns": [], "sizes": [], "stock": {"available": 10},
         "assets": [{"id": 1, "type": "display", "url": "https://img.printfection.com/a.png"}]}]))
    res = await _server().call_tool("list_products", {"page": 2, "limit": 50})
    assert res.is_error is False
    p = res.structured_content["products"][0]
    assert p["id"] == "2" and p["title"] == "Amazing Water Bottle" and p["stock"] == 10 and p["image_url"] == "https://img.printfection.com/a.png"
    req = respx.calls.last.request
    assert req.url.params["limit"] == "50" and req.url.params["offset"] == "50"
    assert req.headers["Authorization"] == "Basic " + base64.b64encode(b"pf-secret:").decode()


@pytest.mark.asyncio
@respx.mock
async def test_create_order_targets_the_collection_campaign():
    route = respx.post(f"{BASE}/orders").mock(return_value=httpx.Response(200, json={
        "id": 1, "object": "order", "status": "open", "created_at": "2014-09-12T10:22:37Z", "campaign": {"id": 2}, "lineitems": []}))
    res = await _server({"api_key": "pf-secret", "campaign_id": "2"}).call_tool("create_order", {
        "items": [{"item_id": 1, "size_id": 2, "quantity": 3}], "shipping_address": {"name": "Joseph Schmo", "city": "Denver", "country": "United States"}})
    assert res.is_error is False and res.structured_content["id"] == "1" and res.structured_content["status"] == "open"
    assert json.loads(route.calls.last.request.content) == {"campaign_id": 2, "ship_to": {"name": "Joseph Schmo", "city": "Denver", "country": "United States"},
                                                          "lineitems": [{"item_id": 1, "size_id": 2, "quantity": 3}]}


@pytest.mark.asyncio
@respx.mock
async def test_track_reads_manifest_shipments():
    respx.get(f"{BASE}/orders/1").mock(return_value=httpx.Response(200, json={"id": 1, "status": "shipped", "manifest": {"total": 12.5, "shipments": [
        {"carrier": "UPS", "method": "UPS Ground", "tracking_numbers": ["1ZA826E90376588070"], "created_at": "2014-09-13T12:21:37Z"}]}}))
    res = await _server().call_tool("track", {"order_id": "1"})
    ev = res.structured_content["events"]
    assert ev[0]["tracking_number"] == "1ZA826E90376588070" and ev[0]["carrier"] == "UPS"


@pytest.mark.asyncio
@respx.mock
async def test_unauthorized_is_an_auth_error_without_the_key():
    respx.get(f"{BASE}/campaigns").mock(return_value=httpx.Response(401, json={"error": "invalid api key pf-secret"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "pf-secret" not in json.dumps(res.structured_content)
