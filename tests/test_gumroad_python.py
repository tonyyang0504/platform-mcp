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

SPEC = json.loads((ROOT / "catalog" / "marketplaces" / "gumroad.json").read_text(encoding="utf-8"))
BASE = "https://api.gumroad.com/v2"


def _server(creds=None):
    # the envelope {success, message} is how Gumroad reports failures inside a body
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], creds or {"access_token": "gum_test_secret"}, 50, "test", envelope=SPEC["adapter"]["envelope"])
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_marketplace_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["create_product", "get_product", "list_products", "list_sales", "me", "refund", "update_price"]  # stats and refunds list not offered
    cp = next(t for t in tools if t.name == "create_product")
    assert cp.annotations.read_only_hint is False and cp.annotations.destructive_hint is False and cp.input_schema["required"] == ["name", "price", "currency"]
    rf = next(t for t in tools if t.name == "refund")
    assert rf.annotations.destructive_hint is True and rf.meta["platform_mcp/endpoint"] == "/sales/{sale_id}/refund"
    ls = next(t for t in tools if t.name == "list_sales")
    assert ls.annotations.read_only_hint is True and ls.meta["platform_mcp/docs"] == "https://app.gumroad.com/api"


@pytest.mark.asyncio
@respx.mock
async def test_list_sales_filters_by_date_and_product_and_maps_the_sale_in_cents():
    # app.gumroad.com/api GET /sales?after&product_id -> {success, next_page_key, sales[]}
    respx.get(f"{BASE}/sales").mock(return_value=httpx.Response(200, json={
        "success": True, "next_page_key": "20230119081040000000-123456",
        "sales": [{"id": "B28UKN-dvxYabdavG97Y-Q==", "email": "calvin@gumroad.com", "created_at": "2021-01-05T19:38:56Z", "product_name": "Pencil Icon PSD", "price": 1000,
                   "gumroad_fee": 60, "currency": "usd", "product_id": "32-nPainqpLj1B_WIwVlMw==", "product_permalink": "XCBbJ", "partially_refunded": False, "chargedback": False,
                   "order_id": 524459995, "disputed": False, "refunded": False, "paid": True}]}))
    res = await _server().call_tool("list_sales", {"since": "2020-09-03", "product_id": "32-nPainqpLj1B_WIwVlMw==", "page": 3, "limit": 20})
    assert res.is_error is False
    s = res.structured_content["sales"][0]
    assert s["id"] == "B28UKN-dvxYabdavG97Y-Q==" and s["product_id"] == "32-nPainqpLj1B_WIwVlMw==" and s["product_name"] == "Pencil Icon PSD"
    assert s["amount"] == 1000 and s["currency"] == "usd" and s["customer_email"] == "calvin@gumroad.com" and s["refunded"] is False and "status" not in s
    req = respx.calls.last.request
    assert req.url.params["after"] == "2020-09-03" and req.url.params["product_id"] == "32-nPainqpLj1B_WIwVlMw==" and "page" not in req.url.params and "page_key" not in req.url.params
    assert req.headers["Authorization"] == "Bearer gum_test_secret" and "access_token" not in req.url.params


@pytest.mark.asyncio
@respx.mock
async def test_create_product_saves_a_draft_with_the_price_in_the_smallest_unit():
    route = respx.post(f"{BASE}/products").mock(return_value=httpx.Response(200, json={
        "success": True, "product": {"id": "A-m3CDDC5dlrSdKZp0RFhA==", "name": "Pencil Icon PSD", "description": "I made this for fun.", "price": 100, "currency": "usd",
                                     "published": False, "deleted": False, "short_url": "https://sahil.gumroad.com/l/pencil", "sales_count": 0}}))
    res = await _server().call_tool("create_product", {"name": "Pencil Icon PSD", "description": "I made this for fun.", "price": 100, "currency": "usd", "url": "https://example.com/ignored"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["id"] == "A-m3CDDC5dlrSdKZp0RFhA==" and sc["price"] == 100 and sc["currency"] == "usd" and sc["url"] == "https://sahil.gumroad.com/l/pencil" and sc["raw"]["published"] is False
    assert json.loads(route.calls.last.request.content) == {"name": "Pencil Icon PSD", "description": "I made this for fun.", "price": 100, "price_currency_type": "usd", "draft": True}
    assert route.calls.last.request.headers["Authorization"] == "Bearer gum_test_secret"


@pytest.mark.asyncio
@respx.mock
async def test_refund_sends_amount_cents_only_for_a_partial_refund():
    route = respx.put(f"{BASE}/sales/A-m3CDDC5dlrSdKZp0RFhA==/refund").mock(return_value=httpx.Response(200, json={
        "success": True, "sale": {"id": "A-m3CDDC5dlrSdKZp0RFhA==", "email": "calvin@gumroad.com", "created_at": "2021-01-23T18:24:07Z", "price": 1000, "currency": "usd", "refunded": False, "partially_refunded": True}}))
    res = await _server().call_tool("refund", {"sale_id": "A-m3CDDC5dlrSdKZp0RFhA==", "amount": 200, "reason": "ignored"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["id"] == "A-m3CDDC5dlrSdKZp0RFhA==" and sc["sale_id"] == sc["id"] and sc["amount"] == 1000 and sc["raw"]["partially_refunded"] is True
    assert json.loads(route.calls.last.request.content) == {"amount_cents": 200}
    res = await _server().call_tool("refund", {"sale_id": "A-m3CDDC5dlrSdKZp0RFhA=="})
    assert res.is_error is False and json.loads(route.calls.last.request.content) == {}  # full refund


@pytest.mark.asyncio
@respx.mock
async def test_body_level_failures_and_refused_tokens_are_error_results_without_the_secret():
    respx.get(f"{BASE}/products/nope").mock(return_value=httpx.Response(200, json={"success": False, "message": "The product could not be found."}))
    res = await _server().call_tool("get_product", {"product_id": "nope"})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error" and "could not be found" in res.structured_content["message"]
    respx.get(f"{BASE}/user").mock(return_value=httpx.Response(401, json={"success": False, "message": "access_token=gum_test_secret is invalid"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 401
    assert "gum_test_secret" not in json.dumps(res.structured_content)
