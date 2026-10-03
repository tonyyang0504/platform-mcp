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

SPEC = json.loads((ROOT / "catalog" / "marketplaces" / "shopify_app_store.json").read_text(encoding="utf-8"))
G = "https://partners.shopify.com/4242/api/2026-07/graphql.json"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {"access_token": "prtapi_secret_1", "organization_id": "4242"}, 50, "test", envelope=a["envelope"]))


@pytest.mark.asyncio
async def test_tools_follow_the_marketplaces_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_product", "list_refunds", "list_sales", "me"]


@pytest.mark.asyncio
@respx.mock
async def test_list_sales_queries_app_sale_transactions_on_the_org_endpoint():
    route = respx.post(G).mock(return_value=httpx.Response(200, json={"data": {"transactions": {"edges": [{"node": {
        "__typename": "AppSubscriptionSale", "id": "gid://partners/AppSubscriptionSale/1", "createdAt": "2026-09-01T00:00:00Z",
        "netAmount": {"amount": "8.00", "currencyCode": "USD"}, "grossAmount": {"amount": "10.00", "currencyCode": "USD"},
        "app": {"id": "gid://partners/App/1234", "name": "Acme"}, "shop": {"myshopifyDomain": "x.myshopify.com", "name": "X"}}}], "pageInfo": {"hasNextPage": False}}}}))
    res = await _server().call_tool("list_sales", {"since": "2026-09-01T00:00:00Z", "product_id": "gid://partners/App/1234", "limit": 10})
    s = res.structured_content["sales"][0]
    assert s["amount"] == "8.00" and s["currency"] == "USD" and s["product_name"] == "Acme" and s["status"] == "AppSubscriptionSale"
    req = route.calls.last.request
    body = json.loads(req.content)
    assert body["variables"] == {"first": 10, "createdAtMin": "2026-09-01T00:00:00Z", "appId": "gid://partners/App/1234"}
    assert "APP_SUBSCRIPTION_SALE" in body["query"] and req.headers["X-Shopify-Access-Token"] == "prtapi_secret_1"


@pytest.mark.asyncio
@respx.mock
async def test_list_refunds_reads_sale_adjustments():
    respx.post(G).mock(return_value=httpx.Response(200, json={"data": {"transactions": {"edges": [{"node": {
        "__typename": "AppSaleAdjustment", "id": "gid://partners/AppSaleAdjustment/9", "createdAt": "2026-09-03T00:00:00Z", "chargeId": "gid://shopify/AppSubscription/5",
        "netAmount": {"amount": "-8.00", "currencyCode": "USD"}}}], "pageInfo": {"hasNextPage": False}}}}))
    res = await _server().call_tool("list_refunds", {})
    r = res.structured_content["refunds"][0]
    assert r["amount"] == "-8.00" and r["sale_id"] == "gid://shopify/AppSubscription/5"


@pytest.mark.asyncio
@respx.mock
async def test_graphql_errors_and_401_never_leak_the_token():
    respx.post(G).mock(return_value=httpx.Response(200, json={"data": None, "errors": [{"message": "Access denied for transactions field."}]}))
    res = await _server().call_tool("list_sales", {})
    assert res.is_error is True
    respx.post(G).mock(return_value=httpx.Response(401, json={"errors": "Invalid token prtapi_secret_1"}))
    res = await _server().call_tool("me", {})
    assert res.structured_content["error"] == "auth_error" and "prtapi_secret_1" not in json.dumps(res.structured_content)
