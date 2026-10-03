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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "sticker_mule.json").read_text(encoding="utf-8"))


def _server(creds=None):
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], creds or {"api_key": "smk-secret"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["create_order", "list_products", "me"]
    co = next(t for t in tools if t.name == "create_order")
    assert co.annotations.read_only_hint is False and co.annotations.destructive_hint is True
    assert co.meta["platform_mcp/docs"] == "https://www.stickermule.com/api"


@pytest.mark.asyncio
@respx.mock
async def test_list_products_reads_reorderable_items_with_offset_paging():
    # stickermule.com/api: GET /api/items -> {items: [...], canLoadMore}
    respx.get("https://www.stickermule.com/api/items").mock(return_value=httpx.Response(200, json={"items": [
        {"id": "456", "name": "Logo stickers", "productId": 12, "productName": "Die cut stickers", "quantity": 50,
         "size": {"__typename": "RegularItemDimensions", "width": 3, "height": 3}, "isSizeRequired": False,
         "buyingOptions": {"quantity": {"min": 50, "max": 5000, "increment": 5}}, "retailPrice": 79,
         "artworkUrls": ["https://cdn.stickermule.com/artwork.png"]},
        {"id": "999", "name": None, "productId": 3, "productName": None, "quantity": 10, "isSizeRequired": False,
         "buyingOptions": None, "retailPrice": None, "artworkUrls": []}], "canLoadMore": True}))
    res = await _server({"api_key": "smk-secret", "currency": "EUR"}).call_tool("list_products", {"page": 3, "limit": 10})
    assert res.is_error is False
    p = res.structured_content["products"]
    assert len(p) == 1  # the unavailable product (productName null) is dropped
    assert p[0]["id"] == "456" and p[0]["title"] == "Die cut stickers" and p[0]["price"] == 79
    assert p[0]["image_url"] == "https://cdn.stickermule.com/artwork.png" and p[0]["min_quantity"] == 50
    req = respx.calls.last.request
    assert req.url.params["limit"] == "10" and req.url.params["offset"] == "20" and req.url.params["currency"] == "EUR"
    assert "locale" not in req.url.params
    assert req.headers["Authorization"] == "Bearer smk-secret"


@pytest.mark.asyncio
@respx.mock
async def test_create_order_sends_saved_address_and_payment_ids():
    route = respx.post("https://www.stickermule.com/api/orders").mock(return_value=httpx.Response(200, json={"order": {"number": "R286234605"}}))
    res = await _server({"api_key": "smk-secret", "payment_id": "7"}).call_tool("create_order", {
        "items": [{"id": "456", "quantity": 50}], "shipping_address": {"id": 22, "name": "Jane Doe"}, "shipping_option": "express"})
    assert res.is_error is False and res.structured_content["id"] == "R286234605"
    assert json.loads(route.calls.last.request.content) == {"items": [{"id": "456", "quantity": 50}], "addressId": "22", "paymentId": "7"}


@pytest.mark.asyncio
@respx.mock
async def test_invalid_key_is_an_auth_error_without_leaking_it():
    respx.get("https://www.stickermule.com/api/items").mock(return_value=httpx.Response(403, json={"type": "ForbiddenError", "message": "invalid key smk-secret"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "smk-secret" not in json.dumps(res.structured_content)
