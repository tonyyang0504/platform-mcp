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

SPEC = json.loads((ROOT / "catalog" / "marketplaces" / "circle.json").read_text(encoding="utf-8"))
CHARGES = "https://app.circle.so/api/admin/v2/community_member_charges"


def _server(creds=None):
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], creds or {"admin_token": "circle_test_secret"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_the_charge_side_of_the_vocabulary_is_served():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["list_refunds", "list_sales", "me", "refund"]  # paywalls have no list/read/create endpoint in Admin API v2
    assert set(SPEC["adapter"]["not_offered"]) == {"list_products", "get_product", "create_product", "update_price", "get_sales_stats"}
    rf = next(t for t in tools if t.name == "refund")
    assert rf.annotations.read_only_hint is False and rf.annotations.destructive_hint is True and rf.input_schema["required"] == ["sale_id"]
    ls = next(t for t in tools if t.name == "list_sales")
    assert ls.annotations.read_only_hint is True and ls.meta["platform_mcp/endpoint"] == "/api/admin/v2/community_member_charges"
    assert next(t for t in tools if t.name == "me").meta["platform_mcp/endpoint"] == "/api/admin/v2/community"


@pytest.mark.asyncio
@respx.mock
async def test_list_sales_pages_the_charges_and_maps_the_documented_record():
    # api-headless.circle.so/api/admin/v2/swagger.yaml: GET community_member_charges -> {page, per_page, has_next_page, count, page_count, records[]}
    respx.get(CHARGES).mock(return_value=httpx.Response(200, json={
        "page": 2, "per_page": 1, "has_next_page": True, "count": 3, "page_count": 3,
        "records": [{"id": 1, "processor_id": "pi_abc123", "status": "paid", "refundable": True, "amount": 1000, "amount_refunded": 0, "currency": "usd", "platform": "web",
                     "created_at": "2021-01-01T00:00:00Z", "paywall_id": 7, "paywall_name": "Premium Membership", "paywall_price_type": "subscription",
                     "community_member_id": 1, "community_member_name": "Jane Doe", "community_member_email": "jane@example.com"}]}))
    res = await _server().call_tool("list_sales", {"product_id": "7", "since": "2020-12-01T00:00:00Z", "page": 2, "limit": 1})
    assert res.is_error is False
    sc = res.structured_content
    s = sc["sales"][0]
    assert s["id"] == "1" and s["product_id"] == "7" and s["product_name"] == "Premium Membership" and s["amount"] == 1000 and s["currency"] == "usd"
    assert s["status"] == "paid" and s["customer_email"] == "jane@example.com" and s["created_at"] == "2021-01-01T00:00:00Z"
    assert sc["total"] == 3 and sc["next_page"] == 3
    req = respx.calls.last.request
    assert req.url.params["page"] == "2" and req.url.params["per_page"] == "1" and req.url.params["paywall_ids"] == "7" and req.url.params["created_at_gte"] == "2020-12-01T00:00:00Z"
    assert req.headers["Authorization"] == "Bearer circle_test_secret"


@pytest.mark.asyncio
@respx.mock
async def test_list_refunds_is_the_refunded_charge_filter():
    respx.get(CHARGES).mock(return_value=httpx.Response(200, json={"page": 1, "per_page": 25, "has_next_page": False, "count": 1, "page_count": 1,
        "records": [{"id": 5, "status": "partial_refunded", "amount": 1000, "amount_refunded": 200, "currency": "usd", "created_at": "2021-01-01T00:00:00Z"}]}))
    res = await _server().call_tool("list_refunds", {"since": "2020-12-01"})
    assert res.is_error is False
    r = res.structured_content["refunds"][0]
    assert r["id"] == "5" and r["sale_id"] == "5" and r["amount"] == 200 and r["status"] == "partial_refunded" and res.structured_content["total"] == 1
    p = respx.calls.last.request.url.params
    assert p["status"] == "refunded,partial_refunded" and p["created_at_gte"] == "2020-12-01" and p["per_page"] == "25"


@pytest.mark.asyncio
@respx.mock
async def test_refund_posts_subunits_and_the_required_reason():
    route = respx.post(f"{CHARGES}/1/refund").mock(return_value=httpx.Response(200, json={
        "id": 1, "status": "partial_refunded", "refundable": True, "amount": 1000, "amount_refunded": 200, "currency": "usd", "created_at": "2021-01-01T00:00:00Z"}))
    res = await _server().call_tool("refund", {"sale_id": "1", "amount": 200, "reason": "duplicate charge"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["id"] == "1" and sc["sale_id"] == "1" and sc["amount"] == 200 and sc["status"] == "partial_refunded" and sc["currency"] == "usd"
    assert json.loads(route.calls.last.request.content) == {"amount": 200, "reason_details": "duplicate charge"}
    assert route.calls.last.request.headers["Authorization"] == "Bearer circle_test_secret"
    route.mock(return_value=httpx.Response(422, json={"success": False, "message": "reason_details is required", "error_details": None}))
    res = await _server().call_tool("refund", {"sale_id": "1"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input" and res.structured_content["http_status"] == 422


@pytest.mark.asyncio
@respx.mock
async def test_refused_token_is_an_auth_error_without_leaking_the_secret():
    respx.get("https://app.circle.so/api/admin/v2/community").mock(return_value=httpx.Response(401, json={"success": False, "message": "Invalid token=circle_test_secret"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 401
    assert "circle_test_secret" not in json.dumps(res.structured_content)
