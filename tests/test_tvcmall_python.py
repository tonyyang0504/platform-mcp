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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "tvcmall.json").read_text(encoding="utf-8"))
BASE = "https://openapi.tvc-mall.com"


def _server(creds=None):
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], creds or {"authorization_token": "2+s8CDVEwkmRHSJ9lorE5Q=="}, 50, "test", envelope=a.get("envelope"))
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_order", "get_product", "me", "quote_shipping"]
    assert all(t.annotations.read_only_hint for t in tools)


@pytest.mark.asyncio
@respx.mock
async def test_get_product_reads_detail_with_the_tvc_prefixed_token():
    respx.get(f"{BASE}/OpenApi/Product/Detail").mock(return_value=httpx.Response(200, json={"Detail": {
        "ItemNo": "660166037C", "Name": "For iPhone 14 Case - Mint Green", "Price": 1.23, "ProductStatus": 1, "MOQ": 1, "CategoryCode": "C003700020098", "StockStatus": 2}}))
    res = await _server().call_tool("get_product", {"id": "660166037C"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["id"] == "660166037C" and sc["title"] == "For iPhone 14 Case - Mint Green" and sc["price"] == 1.23
    req = respx.calls.last.request
    assert req.url.params["ItemNo"] == "660166037C"
    assert req.headers["Authorization"] == "TVC 2+s8CDVEwkmRHSJ9lorE5Q=="


@pytest.mark.asyncio
@respx.mock
async def test_quote_shipping_builds_the_sku_quantity_string():
    route = respx.post(f"{BASE}/order/shippingcost").mock(return_value=httpx.Response(200, json={
        "Success": True, "Currency": "USD", "CountryCode": "US", "Reason": "",
        "Shippings": [{"ShippingMethodCode": "EUDDP", "ShippingMethod": "YunExpress", "ShippingCost": 5.31, "DeliveryCycle": "8-12 business days"}]}))
    res = await _server().call_tool("quote_shipping", {"product_id": "660402384A", "country": "US", "quantity": 2})
    assert res.is_error is False
    assert res.structured_content["options"][0]["id"] == "EUDDP" and res.structured_content["options"][0]["cost"] == 5.31
    assert json.loads(route.calls.last.request.content) == {"skuinfo": "660402384A*2", "countrycode": "US"}


@pytest.mark.asyncio
@respx.mock
async def test_unauthorized_200_body_is_an_auth_error_without_the_token():
    respx.get(f"{BASE}/order/Info").mock(return_value=httpx.Response(200, json={"Message": "unauthorized"}))
    res = await _server().call_tool("get_order", {"id": "V23120200014"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "2+s8CDVEwkmRHSJ9lorE5Q==" not in json.dumps(res.structured_content)


@pytest.mark.asyncio
@respx.mock
async def test_get_order_maps_amounts_and_tracking():
    respx.get(f"{BASE}/order/Info").mock(return_value=httpx.Response(200, json={
        "OrderID": "V23120200014", "Currency": {"CurrencyCode": "USD"}, "OriginalAmount": 1501.72, "DiscountedAmount": 1425.88,
        "ShippingMethodName": "", "Trackingnumbers": ["YT123"], "CreatedOn": "2023-12-02T03:05:28", "ModifiedOn": "2023-12-04T07:28:03", "Items": []}))
    sc = (await _server().call_tool("get_order", {"id": "V23120200014"})).structured_content
    assert sc["id"] == "V23120200014" and sc["total"] == 1425.88 and sc["currency"] == "USD" and sc["tracking_number"] == "YT123"
