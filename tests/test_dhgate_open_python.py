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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "dhgate_open.json").read_text(encoding="utf-8"))
ROUTER = "https://api.dhgate.com/dop/router"
TOKEN = "https://secure.dhgate.com/dop/oauth2/access_token"
CREDS = {"client_id": "APPKEY", "client_secret": "APPSECRET", "refresh_token": "REFRESH-1"}
OK = {"code": "00000000", "message": "OK", "solution": "", "subErrors": []}


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope"))
    return build_server(SPEC, transport=t)


def _token():
    return respx.post(TOKEN).mock(return_value=httpx.Response(200, json={
        "access_token": "ACCESS-1", "expires_in": "864000000", "scope": "basic", "refresh_token": "REFRESH-2"}))


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary():
    tools = {t.name: t for t in await _server().list_tools()}
    assert sorted(tools) == ["create_order", "get_order", "get_product", "list_products", "me", "quote_shipping"]
    assert tools["create_order"].annotations.destructive_hint is True


@pytest.mark.asyncio
@respx.mock
async def test_list_products_refreshes_a_token_and_calls_the_router():
    tok = _token()
    route = respx.get(ROUTER).mock(return_value=httpx.Response(200, json={"status": OK, "pageTotal": "3", "total": "3", "itemList": [
        {"itemCode": 202325055, "itemName": "Bed Canopy Netting", "minBuyerPrice": 23.0, "maxBuyerPrice": 30.0, "imgUrl": "f2/albu/g1/x.jpg", "supplierid": "ff80"}]}))
    res = await _server().call_tool("list_products", {"query": "net", "page": 2, "limit": 20})
    assert res.is_error is False
    p = res.structured_content["products"][0]
    assert p["id"] == "202325055" and p["title"] == "Bed Canopy Netting" and p["price"] == 23.0 and p["currency"] == "USD"
    form = dict(x.split("=", 1) for x in tok.calls.last.request.content.decode().split("&"))
    assert form["grant_type"] == "refresh_token" and form["refresh_token"] == "REFRESH-1" and form["client_id"] == "APPKEY" and form["scope"] == "basic"
    q = route.calls.last.request.url.params
    assert q["method"] == "dh.dropshipping.item.list" and q["v"] == "1.0" and q["access_token"] == "ACCESS-1"
    assert q["pages"] == "2" and q["pageSize"] == "20" and q["itemNameKeyWords"] == "net" and q["timestamp"].isdigit()


@pytest.mark.asyncio
@respx.mock
async def test_quote_shipping_and_get_order_map_fields():
    _token()
    respx.get(ROUTER, params={"method": "dh.dropshipping.ship.get"}).mock(return_value=httpx.Response(200, json={"status": OK, "shipCostAndWayList": [
        {"expressType": "ePacket", "shipcost": 3.5, "currency": "USD", "deliveryTime": "8-30"}]}))
    respx.get(ROUTER, params={"method": "dh.buyer.order.get"}).mock(return_value=httpx.Response(200, json={"status": OK,
        "orderNo": "1330312162", "orderStatus": "103001", "orderTotalPrice": 100.0, "startedDate": "2014-01-12 18:20:21",
        "orderDeliveryList": [{"deliveryNo": "1Z68A9X70467731838", "shippingType": "UPS"}]}))
    s = _server()
    q = await s.call_tool("quote_shipping", {"product_id": "202325055", "country": "US", "quantity": 2})
    assert q.structured_content["options"][0]["id"] == "ePacket" and q.structured_content["options"][0]["cost"] == 3.5
    o = (await s.call_tool("get_order", {"id": "1330312162"})).structured_content
    assert o["id"] == "1330312162" and o["status"] == "103001" and o["total"] == 100.0 and o["tracking_number"] == "1Z68A9X70467731838"


@pytest.mark.asyncio
@respx.mock
async def test_create_order_posts_cart_and_contact_as_json_strings():
    _token()
    route = respx.post(ROUTER).mock(return_value=httpx.Response(200, json={"status": OK, "orderList": [
        {"orderInfo": {"id": 985776655, "orderTotal": 69.6, "shipCost": 0.0, "createTime": 1626832806000}}]}))
    items = [{"itemcode": 634706114, "skuMd5": "562e86410bd37a7bb4170cfe6e03203f", "quantity": 5, "shipType": "ePacket"}]
    addr = {"firstname": "zhao", "lastname": "yiyi", "country": "US", "state": "California", "city": "Chicago", "addressline1": "1 Main St", "postalcode": "12345", "tel": "1311111111"}
    res = await _server().call_tool("create_order", {"items": items, "shipping_address": addr})
    assert res.is_error is False and res.structured_content["id"] == "985776655" and res.structured_content["total"] == 69.6
    req = route.calls.last.request
    assert req.url.params["method"] == "dh.buyer.order.place" and req.url.params["v"] == "2.0"
    from urllib.parse import parse_qs
    form = parse_qs(req.content.decode())
    assert json.loads(form["cartList"][0]) == items and json.loads(form["contactInfo"][0]) == addr


@pytest.mark.asyncio
@respx.mock
async def test_router_error_in_a_200_body_is_an_error_without_secrets():
    _token()
    respx.get(ROUTER).mock(return_value=httpx.Response(200, json={"code": "40", "message": "Access Token expired or not exist ACCESS-1", "solution": "apply again"}))
    res = await _server().call_tool("get_product", {"id": "202325055"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "ACCESS-1" not in json.dumps(res.structured_content)
