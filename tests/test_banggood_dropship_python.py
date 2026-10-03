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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "banggood_dropship.json").read_text(encoding="utf-8"))
BASE = "https://api.banggood.com"


def _server(**extra):
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], {"app_id": "APPID", "app_secret": "bg-secret-77", **extra}, 50, "test", envelope=a["envelope"])
    return build_server(SPEC, transport=t)


def _token():
    # api.banggood.com article 8: GET /getAccessToken?app_id=&app_secret= -> {code: 0, access_token, expires_in: 7200}
    return respx.get(f"{BASE}/getAccessToken").mock(return_value=httpx.Response(200, json={"code": 0, "access_token": "TOK123", "expires_in": 7200}))


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_order", "get_product", "list_products", "me", "quote_shipping", "track"]


@pytest.mark.asyncio
@respx.mock
async def test_list_products_logs_in_and_sends_the_token_as_a_query_parameter():
    tok = _token()
    route = respx.get(f"{BASE}/product/getProductList").mock(return_value=httpx.Response(200, json={
        "code": 0, "page": 1, "page_total": 10, "product_total": 188, "page_size": 20, "lang": "en",
        "product_list": [{"product_id": "1083552", "cat_id": 1753, "product_name": "WLtoys 24438 1/24 2.4G 4WD Rock Crawler RC Car", "img": "https://img1.banggood.com/thu/view", "add_date": "2016-09-01 09:59:40"}]}))
    res = await _server().call_tool("list_products", {"category": "1753", "page": 2})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["products"][0]["id"] == "1083552" and sc["total"] == 188
    assert tok.calls.last.request.url.params["app_id"] == "APPID"
    q = route.calls.last.request.url.params
    assert q["access_token"] == "TOK123" and q["cat_id"] == "1753" and q["page"] == "2" and q["lang"] == "en"


@pytest.mark.asyncio
@respx.mock
async def test_quote_shipping_uses_the_warehouse_setting():
    _token()
    route = respx.get(f"{BASE}/product/getShipments").mock(return_value=httpx.Response(200, json={
        "code": 0, "currency": "USD", "shipment_list": [{"shipmethod_code": "cndhl_cndhl", "shipmethod_name": "Expedited Shipping Service", "shipday": "5-8 business days", "shipfee": "10.92"}]}))
    res = await _server(warehouse="CN").call_tool("quote_shipping", {"product_id": "966064", "country": "United States", "quantity": 2})
    assert res.structured_content["options"][0]["fee"] == "10.92"
    q = route.calls.last.request.url.params
    assert q["warehouse"] == "CN" and q["country"] == "United States" and q["quantity"] == "2"


@pytest.mark.asyncio
@respx.mock
async def test_error_code_in_a_200_body_is_a_tool_error_without_secrets():
    respx.get(f"{BASE}/getAccessToken").mock(return_value=httpx.Response(200, json={"code": 31020, "msg": "Error Account bg-secret-77", "lang": "en"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "bg-secret-77" not in json.dumps(res.structured_content)
