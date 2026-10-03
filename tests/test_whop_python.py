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

SPEC = json.loads((ROOT / "catalog" / "marketplaces" / "whop.json").read_text(encoding="utf-8"))
CREDS = {"api_key": "whop_test_secret", "company_id": "biz_1"}


def _server(creds=None):
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], creds or CREDS, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_marketplace_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["create_product", "get_product", "list_products", "list_refunds", "list_sales", "me", "refund", "update_price"]  # get_sales_stats not offered
    cp = next(t for t in tools if t.name == "create_product")
    assert cp.annotations.read_only_hint is False and cp.annotations.destructive_hint is False and cp.input_schema["required"] == ["name", "price", "currency"]
    assert next(t for t in tools if t.name == "refund").annotations.destructive_hint is True
    ls = next(t for t in tools if t.name == "list_sales")
    assert ls.annotations.read_only_hint is True and ls.meta["platform_mcp/endpoint"] == "/payments"
    assert next(t for t in tools if t.name == "me").meta["platform_mcp/endpoint"] == "/accounts/me"


@pytest.mark.asyncio
@respx.mock
async def test_list_sales_scopes_to_the_company_and_maps_the_payment_record():
    # docs.whop.com/api-reference/payments/list-payments
    respx.get("https://api.whop.com/api/v1/payments").mock(return_value=httpx.Response(200, json={
        "data": [{"id": "pay_xxxxxxxxxxxxxx", "status": "paid", "substatus": "succeeded", "total": 29, "subtotal": 29, "currency": "usd",
                  "product": {"id": "prod_xxxxxxxxxxxxx", "title": "Pickaxe Analytics", "route": "pickaxe-analytics", "metadata": {}},
                  "user": {"id": "user_xxxxxxxxxxxxx", "name": "John Doe", "username": "johndoe42", "email": "john@example.com"},
                  "created_at": "2023-12-01T05:00:00.401Z", "paid_at": "2023-12-01T05:00:01.401Z", "refunded_amount": 0, "refunded_at": None}],
        "page_info": {"end_cursor": "abc", "start_cursor": "abc", "has_next_page": False, "has_previous_page": False}}))
    res = await _server().call_tool("list_sales", {"product_id": "prod_xxxxxxxxxxxxx", "since": "2023-11-01T00:00:00Z", "limit": 10})
    assert res.is_error is False
    s = res.structured_content["sales"][0]
    assert s["id"] == "pay_xxxxxxxxxxxxxx" and s["product_id"] == "prod_xxxxxxxxxxxxx" and s["product_name"] == "Pickaxe Analytics" and s["amount"] == 29 and s["currency"] == "usd"
    assert s["status"] == "paid" and s["customer_email"] == "john@example.com" and s["created_at"] == "2023-12-01T05:00:00.401Z"
    assert res.structured_content["next_page"] is None
    req = respx.calls.last.request
    assert req.url.params["account_id"] == "biz_1" and req.url.params["first"] == "10" and req.url.params["created_after"] == "2023-11-01T00:00:00Z" and req.url.params["product_ids"] == "prod_xxxxxxxxxxxxx"
    assert req.headers["Authorization"] == "Bearer whop_test_secret"


@pytest.mark.asyncio
@respx.mock
async def test_create_product_nests_the_plan_options_and_carries_the_company_id():
    # docs.whop.com/api-reference/products/create-product
    route = respx.post("https://api.whop.com/api/v1/products").mock(return_value=httpx.Response(200, json={
        "id": "prod_new", "title": "Pro Plan", "description": "Track your revenue", "visibility": "visible", "route": "pro-plan",
        "created_at": "2023-12-01T05:00:00.401Z", "updated_at": "2023-12-01T05:00:00.401Z", "company": {"id": "biz_1", "route": "pickaxe", "title": "Pickaxe"}}))
    res = await _server().call_tool("create_product", {"name": "Pro Plan", "description": "Track your revenue", "price": 10.43, "currency": "usd", "url": "https://example.com/ignored"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["id"] == "prod_new" and sc["name"] == "Pro Plan" and sc["status"] == "visible" and "price" not in sc  # prices live on plans
    assert json.loads(route.calls.last.request.content) == {"account_id": "biz_1", "title": "Pro Plan", "description": "Track your revenue",
                                                            "plan_options": {"initial_price": 10.43, "base_currency": "usd", "plan_type": "one_time"}}
    assert route.calls.last.request.headers["Authorization"] == "Bearer whop_test_secret"


@pytest.mark.asyncio
@respx.mock
async def test_refund_sends_partial_amount_only_when_given_and_reads_the_refunded_amount():
    # docs.whop.com/api-reference/payments/refund-payment
    route = respx.post("https://api.whop.com/api/v1/payments/pay_1/refund").mock(return_value=httpx.Response(200, json={
        "id": "pay_1", "status": "paid", "currency": "usd", "total": 29, "refunded_amount": 6.9, "refunded_at": "2024-01-02T00:00:00Z", "refundable": True,
        "refunds": [{"id": "ref_1", "status": "succeeded", "amount": 6.9, "currency": "usd", "created_at": "2024-01-02T00:00:00Z"}]}))
    res = await _server().call_tool("refund", {"sale_id": "pay_1", "amount": 6.9, "reason": "goodwill"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["id"] == "pay_1" and sc["sale_id"] == "pay_1" and sc["amount"] == 6.9 and sc["created_at"] == "2024-01-02T00:00:00Z" and sc["raw"]["refunds"][0]["id"] == "ref_1"
    assert json.loads(route.calls.last.request.content) == {"partial_amount": 6.9}  # reason is not accepted by the endpoint
    res = await _server().call_tool("refund", {"sale_id": "pay_1"})
    assert res.is_error is False and json.loads(route.calls.last.request.content) == {}  # full refund


@pytest.mark.asyncio
@respx.mock
async def test_refused_key_is_an_auth_error_without_leaking_the_secret():
    respx.get("https://api.whop.com/api/v1/accounts/me").mock(return_value=httpx.Response(401, json={"error": {"message": "Unauthorized: token=whop_test_secret"}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 401
    assert "whop_test_secret" not in json.dumps(res.structured_content)
