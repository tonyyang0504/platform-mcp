import base64
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

SPEC = json.loads((ROOT / "catalog" / "marketplaces" / "atlassian_marketplace.json").read_text(encoding="utf-8"))
B = "https://marketplace.atlassian.com/rest/2"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {"email": "dev@example.com", "api_token": "atl-secret-token", "vendor_id": "1212"}, 50, "test"))


@pytest.mark.asyncio
async def test_tools_follow_the_marketplaces_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_product", "list_products", "list_refunds", "list_sales", "me"]


@pytest.mark.asyncio
@respx.mock
async def test_list_sales_filters_by_addon_and_date_with_basic_auth():
    route = respx.get(url__startswith=f"{B}/vendors/1212/reporting/sales/transactions").mock(return_value=httpx.Response(200, json={"transactions": [
        {"transactionId": "AT-1", "addonKey": "com.acme.app", "addonName": "Acme", "paymentStatus": "paid", "customerDetails": {"company": "X", "technicalContact": {"email": "it@x.com", "name": "I T"}},
         "purchaseDetails": {"saleDate": "2026-09-01", "purchasePrice": 120.0, "vendorAmount": 102.0, "saleType": "new"}}]}))
    res = await _server().call_tool("list_sales", {"product_id": "com.acme.app", "since": "2026-09-01", "limit": 10})
    s = res.structured_content["sales"][0]
    assert s["id"] == "AT-1" and s["amount"] == 120.0 and s["currency"] == "USD" and s["customer_email"] == "it@x.com"
    req = route.calls.last.request
    p = req.url.params
    assert p["addon"] == "com.acme.app" and p["startDate"] == "2026-09-01" and p["limit"] == "10" and p["offset"] == "0"
    assert req.headers["Authorization"] == "Basic " + base64.b64encode(b"dev@example.com:atl-secret-token").decode()


@pytest.mark.asyncio
@respx.mock
async def test_list_refunds_fixes_sale_type_and_rejects_a_bad_date():
    route = respx.get(url__startswith=f"{B}/vendors/1212/reporting/sales/transactions").mock(return_value=httpx.Response(200, json={"transactions": [
        {"transactionId": "AT-9", "paymentStatus": "refunded", "purchaseDetails": {"saleDate": "2026-09-03", "purchasePrice": -120.0, "refundReason": "Customer request", "saleType": "refund", "originalTransactionDetails": {"transactionId": "AT-1"}}}]}))
    res = await _server().call_tool("list_refunds", {})
    r = res.structured_content["refunds"][0]
    assert r["sale_id"] == "AT-1" and r["reason"] == "Customer request" and route.calls.last.request.url.params["saleType"] == "refund"
    res = await _server().call_tool("list_refunds", {"since": "yesterday"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input"


@pytest.mark.asyncio
@respx.mock
async def test_probe_401_is_an_auth_error_without_the_token():
    respx.get(url__startswith=f"{B}/vendors/1212/reporting/sales/transactions").mock(return_value=httpx.Response(401, text="Unauthorized for atl-secret-token"))
    res = await _server().call_tool("me", {})
    assert res.structured_content["error"] == "auth_error" and "atl-secret-token" not in json.dumps(res.structured_content)
