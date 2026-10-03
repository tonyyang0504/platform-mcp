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

SPEC = json.loads((ROOT / "catalog" / "marketplaces" / "digistore24.json").read_text(encoding="utf-8"))
BASE = "https://www.digistore24.com/api/call"


def _server(creds=None):
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], creds or {"api_key": "ds24_test_secret"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_every_marketplace_verb_is_served_with_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["create_product", "get_product", "get_sales_stats", "list_products", "list_refunds", "list_sales", "me", "refund", "update_price"]
    rf = next(t for t in tools if t.name == "refund")
    assert rf.annotations.read_only_hint is False and rf.annotations.destructive_hint is True and rf.meta["platform_mcp/endpoint"] == "/refundPurchase"
    up = next(t for t in tools if t.name == "update_price")
    assert up.annotations.destructive_hint is False and up.meta["platform_mcp/endpoint"] == "/createPaymentplan"
    ls = next(t for t in tools if t.name == "list_sales")
    assert ls.annotations.read_only_hint is True and ls.meta["platform_mcp/docs"] == "https://digistore24.com/api/docs/paths/listPurchases.yaml"


@pytest.mark.asyncio
@respx.mock
async def test_list_sales_sends_the_documented_query_with_the_api_key_header_and_maps_purchases():
    # digistore24.com/api/docs/paths/listPurchases.yaml: GET listPurchases?from&search[product_id]&page_no&page_size, envelope {result, data}
    respx.get(f"{BASE}/listPurchases").mock(return_value=httpx.Response(200, json={
        "api_version": "1.234", "current_time": "2026-09-24 10:00:00", "result": "success",
        "data": {"purchase_list": [{"purchase_id": "X26QE8GN", "product_id": 39, "product_name": "The Weight Loss Cake", "amount": 29.9, "currency": "EUR",
                                    "payment_status": "paid", "buyer_email": "uw@ds24mail.com", "created_at": "2026-09-20 12:00:00", "payplan_id": "7", "click_id": ""}]}}))
    res = await _server().call_tool("list_sales", {"since": "2026-09-01", "product_id": "39", "page": 2, "limit": 50})
    assert res.is_error is False
    s = res.structured_content["sales"][0]
    assert s["id"] == "X26QE8GN" and s["product_id"] == "39" and s["product_name"] == "The Weight Loss Cake" and s["amount"] == 29.9 and s["currency"] == "EUR"
    assert s["status"] == "paid" and s["customer_email"] == "uw@ds24mail.com" and s["created_at"] == "2026-09-20 12:00:00"
    req = respx.calls.last.request
    p = req.url.params
    assert p["from"] == "2026-09-01" and p["search[product_id]"] == "39" and p["page_no"] == "2" and p["page_size"] == "50" and p["sort_by"] == "date" and p["sort_order"] == "desc"
    assert req.headers["X-DS-API-KEY"] == "ds24_test_secret" and "Authorization" not in req.headers


@pytest.mark.asyncio
@respx.mock
async def test_create_product_and_update_price_pass_bracketed_data_parameters_without_a_json_body():
    # digistore24.com/api/docs/paths/createProduct.yaml (data[...] query parameters) -> data{product_id}
    route = respx.post(f"{BASE}/createProduct").mock(return_value=httpx.Response(200, json={"api_version": "1.234", "result": "success", "data": {"product_id": 4711}}))
    res = await _server().call_tool("create_product", {"name": "Cake Course", "description": "<p>Learn</p>", "price": 49, "currency": "EUR", "url": "https://example.com/cake"})
    assert res.is_error is False and res.structured_content["id"] == "4711"
    req = route.calls.last.request
    assert req.content == b""  # parameters travel as GET/POST parameters, not JSON
    assert req.url.params["data[name_intern]"] == "Cake Course" and req.url.params["data[name_en]"] == "Cake Course" and req.url.params["data[description_en]"] == "<p>Learn</p>"
    assert req.url.params["data[currency]"] == "EUR" and req.url.params["data[salespage_url]"] == "https://example.com/cake" and "data[first_amount]" not in req.url.params
    # digistore24.com/api/docs/paths/createPaymentplan.yaml -> data{paymentplan_id, rendered_texts, plan}
    route = respx.post(f"{BASE}/createPaymentplan").mock(return_value=httpx.Response(200, json={"result": "success", "data": {"paymentplan_id": 99, "rendered_texts": {}, "plan": {"id": 99, "first_amount": 49, "currency": "EUR", "number_of_installments": 1}}}))
    res = await _server().call_tool("update_price", {"product_id": "4711", "price": 49, "currency": "EUR"})
    assert res.is_error is False and res.structured_content["id"] == "99" and res.structured_content["price"] == 49 and res.structured_content["currency"] == "EUR"
    p = route.calls.last.request.url.params
    assert p["product_id"] == "4711" and p["data[first_amount]"] == "49" and p["data[currency]"] == "EUR" and p["data[number_of_installments]"] == "1"
    assert route.calls.last.request.headers["X-DS-API-KEY"] == "ds24_test_secret"


@pytest.mark.asyncio
@respx.mock
async def test_refund_targets_the_purchase_and_keeps_the_platform_answer_in_raw():
    route = respx.post(f"{BASE}/refundPurchase").mock(return_value=httpx.Response(200, json={"result": "success", "data": {"status": "pending", "modified": "Y", "note": "Refund is being processed", "pending_reason": "default_delay"}}))
    res = await _server().call_tool("refund", {"sale_id": "X26QE8GN", "amount": 10, "reason": "buyer request"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["id"] == "refundPurchase" and sc["status"] == "requested" and sc["raw"]["status"] == "pending"
    p = route.calls.last.request.url.params
    assert p["purchase_id"] == "X26QE8GN" and "amount" not in p and "force" not in p and route.calls.last.request.content == b""


@pytest.mark.asyncio
@respx.mock
async def test_refused_key_is_an_auth_error_without_leaking_the_secret():
    respx.get(f"{BASE}/getUserInfo").mock(return_value=httpx.Response(401, json={"result": "error", "message": "Invalid api_key=ds24_test_secret", "code": "unauthorized"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 401
    assert "ds24_test_secret" not in json.dumps(res.structured_content)
