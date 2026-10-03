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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "peecho.json").read_text(encoding="utf-8"))
BASE = "https://www.peecho.com/rest/v3"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"merchant_api_key": "pc-key-42", "currency": "EUR"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["create_order", "get_order", "me", "quote_shipping"]


@pytest.mark.asyncio
@respx.mock
async def test_quote_shipping_builds_the_quote_request():
    route = respx.post(f"{BASE}/quote").mock(return_value=httpx.Response(200, json={
        "quoteDetails": {"countryCode": "CA", "currency": "EUR"},
        "quotedItems": [{"offeringId": 228478, "quantity": 100, "productPrice": 770.0, "shippingWholesale": 0.18, "totalItemPrice": 577.68}],
        "quoteSummary": {"totalWholesalePrice": 577.68, "totalShippingPrice": 0.18}}))
    res = await _server().call_tool("quote_shipping", {"product_id": "228478", "country": "CA", "quantity": 100})
    assert res.is_error is False and res.structured_content["options"][0]["shipping_wholesale"] == 0.18
    body = json.loads(route.calls.last.request.content)
    assert body == {"apiKey": "pc-key-42", "countryCode": "CA", "currency": "EUR", "items": [{"offeringId": 228478, "quantity": 100}]}


@pytest.mark.asyncio
@respx.mock
async def test_create_then_read_order():
    create = respx.post(f"{BASE}/order/").mock(return_value=httpx.Response(201, json={"order_id": 1234}))
    details = respx.get(f"{BASE}/order/details").mock(return_value=httpx.Response(200, json={"order_id": 1234, "order_state": "OPEN", "currency": "EUR", "created_date": "2026-09-25T10:00:00", "tracking_code": None}))
    s = _server()
    res = await s.call_tool("create_order", {"items": [{"offering_id": 233309, "quantity": 3, "file_details": {"content_url": "https://x/a.pdf"}}],
        "shipping_address": {"email_address": "j@example.com", "shipping_address": {"first_name": "Joshua", "last_name": "Grim", "address_line_1": "Test", "address_line_2": "1", "zip_code": "35100", "city": "Florida", "country_code": "US"}}, "shipping_option": "STANDARD"})
    assert res.structured_content["id"] == "1234"
    body = json.loads(create.calls.last.request.content)
    assert body["merchant_api_key"] == "pc-key-42" and body["address_details"]["email_address"] == "j@example.com" and body["item_details"][0]["offering_id"] == 233309
    got = await s.call_tool("get_order", {"id": "1234"})
    assert got.structured_content["status"] == "OPEN"
    q = details.calls.last.request.url.params
    assert q["orderId"] == "1234" and q["merchantApiKey"] == "pc-key-42"


@pytest.mark.asyncio
@respx.mock
async def test_bad_request_is_invalid_input_without_the_key():
    respx.post(f"{BASE}/order/").mock(return_value=httpx.Response(400, json={"details": "Required quantity: 0 is lower than the minimum quantity of: 1! key pc-key-42", "custom_code": "OFF_MIN"}))
    res = await _server().call_tool("create_order", {"items": [], "shipping_address": {}})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input" and "pc-key-42" not in json.dumps(res.structured_content)
