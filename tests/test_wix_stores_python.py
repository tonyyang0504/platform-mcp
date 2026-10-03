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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "wix_stores.json").read_text(encoding="utf-8"))


def _server():
    # header auth with two credential-carrying headers: the raw API key in Authorization and the site id in wix-site-id
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": "IST.key", "site_id": "site-guid"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_the_expressible_verbs_are_tools():
    tools = await _server().list_tools()
    # catalog writes need the current revision / variant arrays; fulfillments need lineItems[] -> not offered
    assert sorted(t.name for t in tools) == ["list_orders", "me"]
    assert set(SPEC["adapter"]["not_offered"]) == {"create_listing", "update_listing", "end_listing", "set_inventory", "mark_shipped", "listing_metrics"}


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_posts_a_nested_search_with_both_auth_headers():
    # dev.wix.com .../e-commerce/orders/orders/search-orders -> {orders[], metadata}
    route = respx.post("https://www.wixapis.com/ecom/v1/orders/search").mock(return_value=httpx.Response(200, json={
        "orders": [{"id": "d5d43d01-d9e0-4b6b-8f78-5c0e5c5c1c1e", "number": 10021, "createdDate": "2023-11-10T08:28:58.917Z", "status": "APPROVED", "paymentStatus": "PAID", "fulfillmentStatus": "NOT_FULFILLED",
                    "currency": "USD", "priceSummary": {"total": {"amount": "44.00", "formattedAmount": "$44.00"}}}],
        "metadata": {"count": 1, "cursors": {"next": None}, "hasNext": False}}))
    res = await _server().call_tool("list_orders", {"status": "APPROVED", "since": "2023-11-01T00:00:00Z", "limit": 50})
    assert res.is_error is False
    o = res.structured_content["orders"][0]
    assert o["id"] == "d5d43d01-d9e0-4b6b-8f78-5c0e5c5c1c1e" and o["status"] == "APPROVED" and o["total"] == "44.00" and o["currency"] == "USD" and o["created_at"].startswith("2023-11-10")
    req = route.calls.last.request
    assert json.loads(req.content) == {"search": {"cursorPaging": {"limit": 50}, "filter": {"status": "APPROVED", "createdDate": {"$gte": "2023-11-01T00:00:00.000Z"}}}}
    assert req.headers["Authorization"] == "IST.key" and req.headers["wix-site-id"] == "site-guid"


@pytest.mark.asyncio
@respx.mock
async def test_throttling_is_a_rate_limited_result():
    respx.get("https://www.wixapis.com/site-properties/v4/properties").mock(return_value=httpx.Response(429, json={"message": "Too Many Requests"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited"
