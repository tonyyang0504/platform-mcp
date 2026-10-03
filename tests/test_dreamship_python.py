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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "dreamship.json").read_text(encoding="utf-8"))
BASE = "https://api.dreamship.com/v1"


def _server(creds=None):
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], creds or {"api_key": "k"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["create_order", "get_order", "get_product", "list_products", "me"]
    co = next(t for t in tools if t.name == "create_order")
    assert co.annotations.read_only_hint is False and co.annotations.destructive_hint is True
    lp = next(t for t in tools if t.name == "list_products")
    assert lp.meta["platform_mcp/endpoint"] == "/items/" and lp.meta["platform_mcp/docs"] == "https://docs.dreamship.com/reference/listitems"


@pytest.mark.asyncio
@respx.mock
async def test_list_products_reads_data_and_paging_count():
    # docs.dreamship.com/reference/listitems: {paging{count, next, previous}, data[Item]}
    respx.get(f"{BASE}/items/").mock(return_value=httpx.Response(200, json={
        "paging": {"count": 120, "next": "https://api.dreamship.com/v1/items/?page=3", "previous": None},
        "data": [{"id": 101, "name": "Unisex Heavy Cotton Tee", "description": "Gildan 5000", "release_status": "live", "starting_basic_cost": "7.50",
                  "production_days_min": 2, "production_days_max": 4}]}))
    res = await _server().call_tool("list_products", {"page": 2, "limit": 1})
    assert res.is_error is False
    sc = res.structured_content
    p = sc["products"][0]
    assert p["id"] == "101" and p["title"] == "Unisex Heavy Cotton Tee" and p["starting_basic_cost"] == "7.50"
    assert sc["total"] == 120 and sc["next_page"] == 3
    req = respx.calls.last.request
    assert req.url.params["page"] == "2" and req.url.params["limit"] == "1"
    assert req.headers["Authorization"] == "Bearer k"


@pytest.mark.asyncio
@respx.mock
async def test_create_order_sends_address_line_items_and_test_flag():
    route = respx.post(f"{BASE}/orders/").mock(return_value=httpx.Response(201, json={
        "id": 555, "status": "submitted", "created_at": "2026-09-24T10:00:00Z", "total_cost": "12.40", "reference_id": None}))
    addr = {"first_name": "Jo", "last_name": "Doe", "street1": "1 Main St", "city": "Austin", "state": "TX", "zip": "78701", "country": "US", "force_verified_delivery": False}
    items = [{"item_variant": 9001, "quantity": 1, "print_areas": [{"key": "front", "url": "https://x.test/a.png"}]}]
    res = await _server({"api_key": "k", "test_order": "true"}).call_tool("create_order", {"items": items, "shipping_address": addr, "shipping_option": "economy"})
    assert res.is_error is False
    assert res.structured_content["id"] == "555" and res.structured_content["status"] == "submitted"
    body = json.loads(route.calls.last.request.content)
    assert body == {"address": addr, "line_items": items, "shipping_method": "economy", "test_order": "true"}


@pytest.mark.asyncio
@respx.mock
async def test_get_order_reads_first_tracking_and_rate_limit_is_an_error():
    respx.get(f"{BASE}/orders/555/").mock(return_value=httpx.Response(200, json={
        "id": 555, "status": "fulfilled", "created_at": "2026-09-24T10:00:00Z", "total_cost": "12.40", "payment_status": "paid",
        "fulfillments": [{"id": 1, "trackings": [{"carrier": "usps", "status": "transit", "tracking_number": "9400", "tracking_url": "https://t.test/9400"}]}]}))
    res = await _server().call_tool("get_order", {"id": "555"})
    assert res.is_error is False
    assert res.structured_content["tracking_number"] == "9400" and res.structured_content["status"] == "fulfilled"
    respx.get(f"{BASE}/shops/").mock(return_value=httpx.Response(429, headers={"Retry-After": "59"}, json={"error": {"key": "throttled", "status_code": 429}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited"
