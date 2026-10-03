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

SPEC = json.loads((ROOT / "catalog" / "marketplaces" / "paddle.json").read_text(encoding="utf-8"))


def _server(creds=None):
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], creds or {"api_key": "pdl_test_secret"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_marketplace_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["create_product", "get_product", "list_products", "list_refunds", "list_sales", "me", "refund", "update_price"]  # get_sales_stats not offered
    rf = next(t for t in tools if t.name == "refund")
    assert rf.annotations.read_only_hint is False and rf.annotations.destructive_hint is True and rf.input_schema["required"] == ["sale_id"]
    up = next(t for t in tools if t.name == "update_price")
    assert up.annotations.destructive_hint is False and up.annotations.idempotent_hint is True and up.meta["platform_mcp/endpoint"] == "/prices"
    ls = next(t for t in tools if t.name == "list_sales")
    assert ls.annotations.read_only_hint is True and ls.output_schema["properties"]["sales"]["type"] == "array"
    assert ls.meta["platform_mcp/docs"] == "https://developer.paddle.com/api-reference/transactions/list-transactions"


@pytest.mark.asyncio
@respx.mock
async def test_list_products_includes_prices_and_maps_the_first_unit_price():
    # developer.paddle.com/api-reference/products/list-products (include=prices)
    respx.get("https://api.paddle.com/products").mock(return_value=httpx.Response(200, json={
        "data": [{"id": "pro_01gsz4t5hdjse780zja8vvr7jg", "name": "AeroEdit Pro", "description": "Professional plan", "tax_category": "standard", "type": "standard",
                  "status": "active", "created_at": "2023-02-23T12:43:46.605Z", "updated_at": "2024-04-05T15:53:44.687Z",
                  "prices": [{"id": "pri_01gsz8x8sawmvhz1pv30nge1ke", "unit_price": {"amount": "1000", "currency_code": "USD"}, "status": "active"}]}],
        "meta": {"request_id": "r", "pagination": {"per_page": 10, "next": "https://api.paddle.com/products?after=pro_01", "has_more": False, "estimated_total": 1}}}))
    res = await _server().call_tool("list_products", {"status": "active", "limit": 10})
    assert res.is_error is False
    p = res.structured_content["products"][0]
    assert p["id"] == "pro_01gsz4t5hdjse780zja8vvr7jg" and p["name"] == "AeroEdit Pro" and p["price"] == "1000" and p["currency"] == "USD" and p["status"] == "active"
    assert res.structured_content["next_page"] is None and res.structured_content["total"] is None
    req = respx.calls.last.request
    assert req.url.params["include"] == "prices" and req.url.params["per_page"] == "10" and req.url.params["status"] == "active"
    assert req.headers["Authorization"] == "Bearer pdl_test_secret"


@pytest.mark.asyncio
@respx.mock
async def test_update_price_creates_a_price_entity_with_the_documented_unit_price_object():
    # developer.paddle.com/api-reference/prices/create-price: unit_price.amount is a string in the lowest denomination
    route = respx.post("https://api.paddle.com/prices").mock(return_value=httpx.Response(201, json={
        "data": {"id": "pri_02", "product_id": "pro_01", "description": "Price created via platform-mcp update_price", "name": None,
                 "unit_price": {"amount": "1500", "currency_code": "USD"}, "status": "active", "created_at": "2024-04-05T15:53:44.687Z", "updated_at": "2024-04-05T15:53:44.687Z"},
        "meta": {"request_id": "r"}}))
    res = await _server().call_tool("update_price", {"product_id": "pro_01", "price": 1500, "currency": "USD"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["id"] == "pro_01" and sc["price"] == "1500" and sc["currency"] == "USD" and sc["status"] == "active" and sc["raw"]["id"] == "pri_02"
    assert json.loads(route.calls.last.request.content) == {"description": "Price created via platform-mcp update_price", "product_id": "pro_01", "unit_price": {"amount": "1500", "currency_code": "USD"}}
    assert route.calls.last.request.headers["Authorization"] == "Bearer pdl_test_secret"


@pytest.mark.asyncio
@respx.mock
async def test_list_sales_filters_by_created_at_and_refund_is_always_a_full_adjustment():
    respx.get("https://api.paddle.com/transactions").mock(return_value=httpx.Response(200, json={
        "data": [{"id": "txn_01", "status": "completed", "customer_id": "ctm_01", "currency_code": "USD", "origin": "web", "created_at": "2024-04-12T10:18:47.635628Z",
                  "details": {"totals": {"subtotal": "1000", "tax": "0", "total": "1000", "grand_total": "1000", "currency_code": "USD"}},
                  "items": [{"price_id": "pri_01", "quantity": 1, "price": {"product_id": "pro_01", "name": "Monthly"}}],
                  "customer": {"id": "ctm_01", "email": "sam@example.com", "name": "Sam"}}],
        "meta": {"pagination": {"per_page": 30, "has_more": False}}}))
    res = await _server().call_tool("list_sales", {"since": "2024-04-01T00:00:00Z", "product_id": "pro_01", "limit": 50})
    assert res.is_error is False
    s = res.structured_content["sales"][0]
    assert s["id"] == "txn_01" and s["product_id"] == "pro_01" and s["product_name"] == "Monthly" and s["amount"] == "1000" and s["customer_email"] == "sam@example.com"
    params = respx.calls.last.request.url.params
    assert params["created_at[GTE]"] == "2024-04-01T00:00:00Z" and params["include"] == "customer" and params["per_page"] == "30" and "product_id" not in params  # max 30, no product filter
    route = respx.post("https://api.paddle.com/adjustments").mock(return_value=httpx.Response(201, json={
        "data": {"id": "adj_01", "action": "refund", "type": "full", "transaction_id": "txn_01", "reason": "duplicate", "status": "pending_approval", "currency_code": "USD",
                 "totals": {"subtotal": "1000", "tax": "0", "total": "1000", "currency_code": "USD"}, "created_at": "2024-04-13T10:18:47Z"}, "meta": {"request_id": "r"}}))
    res = await _server().call_tool("refund", {"sale_id": "txn_01", "amount": 5, "reason": "duplicate"})
    assert res.is_error is False and res.structured_content["id"] == "adj_01" and res.structured_content["sale_id"] == "txn_01" and res.structured_content["status"] == "pending_approval"
    assert json.loads(route.calls.last.request.content) == {"action": "refund", "transaction_id": "txn_01", "reason": "duplicate", "type": "full"}  # amount never reaches the body


@pytest.mark.asyncio
@respx.mock
async def test_refused_key_is_an_auth_error_without_leaking_the_secret():
    respx.get("https://api.paddle.com/event-types").mock(return_value=httpx.Response(403, json={"error": {"type": "request_error", "code": "forbidden", "detail": "token=pdl_test_secret is not allowed"}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 403
    assert "pdl_test_secret" not in json.dumps(res.structured_content)
