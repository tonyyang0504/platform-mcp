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

SPEC = json.loads((ROOT / "catalog" / "marketplaces" / "lemon_squeezy.json").read_text(encoding="utf-8"))
B = "https://api.lemonsqueezy.com/v1"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {"api_key": "ls-secret-key-123", "store_id": "7"}, 50, "test"))


@pytest.mark.asyncio
async def test_tools_follow_the_marketplaces_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_product", "get_sales_stats", "list_products", "list_sales", "me", "refund"]
    assert next(t for t in tools if t.name == "refund").annotations.destructive_hint is True


@pytest.mark.asyncio
@respx.mock
async def test_list_products_pages_with_json_api_params_and_headers():
    route = respx.get(url__startswith=f"{B}/products").mock(return_value=httpx.Response(200, json={
        "meta": {"page": {"currentPage": 1, "total": 1}}, "data": [{"type": "products", "id": "1", "attributes": {"name": "Lemonade", "price": 999, "status": "published", "buy_now_url": "https://s.lemonsqueezy.com/checkout/buy/x", "created_at": "2024-05-27T12:54:47.000000Z"}}]}))
    res = await _server().call_tool("list_products", {"page": 2, "limit": 10})
    p = res.structured_content["products"][0]
    assert p["id"] == "1" and p["price"] == 999 and p["status"] == "published" and res.structured_content["total"] == 1
    req = route.calls.last.request
    assert req.url.params["page[number]"] == "2" and req.url.params["page[size]"] == "10" and req.url.params["filter[store_id]"] == "7"
    assert req.headers["Accept"] == "application/vnd.api+json" and req.headers["Authorization"] == "Bearer ls-secret-key-123"


@pytest.mark.asyncio
@respx.mock
async def test_partial_refund_sends_a_json_api_document_in_cents():
    route = respx.post(f"{B}/orders/1/refund").mock(return_value=httpx.Response(200, json={"data": {"type": "orders", "id": "1", "attributes": {"currency": "USD", "refunded_amount": 100, "status": "partial_refund", "refunded_at": None}}}))
    res = await _server().call_tool("refund", {"sale_id": "1", "amount": 100})
    assert res.is_error is False and res.structured_content["amount"] == 100 and res.structured_content["status"] == "partial_refund"
    req = route.calls.last.request
    assert json.loads(req.content) == {"data": {"type": "orders", "id": "1", "attributes": {"amount": 100}}}
    assert req.headers["Content-Type"] == "application/vnd.api+json"
    res = await _server().call_tool("refund", {"sale_id": "1", "amount": 1.5})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input"


@pytest.mark.asyncio
@respx.mock
async def test_sales_stats_reads_store_totals_and_401_hides_the_key():
    respx.get(f"{B}/stores/7").mock(return_value=httpx.Response(200, json={"data": {"type": "stores", "id": "7", "attributes": {"total_revenue": 1500000, "total_sales": 1200, "thirty_day_revenue": 25000, "thirty_day_sales": 20, "currency": "USD"}}}))
    res = await _server().call_tool("get_sales_stats", {})
    assert res.structured_content["revenue"] == 1500000 and res.structured_content["sales"] == 1200 and res.structured_content["period"] == "all_time"
    respx.get(f"{B}/users/me").mock(return_value=httpx.Response(401, json={"errors": [{"detail": "Unauthenticated ls-secret-key-123"}]}))
    res = await _server().call_tool("me", {})
    assert res.structured_content["error"] == "auth_error" and "ls-secret-key-123" not in json.dumps(res.structured_content)
