import json
import sys
from pathlib import Path

import httpx
import jwt as pyjwt
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "gmarket_esm.json").read_text(encoding="utf-8"))
SECRET = "gm-secret-key-0123456789-abcdefghij"
CREDS = {"secret_key": SECRET, "master_id": "master_1", "site_seller_ids": "A:iacseller,G:gmkseller", "site_type": "2"}
BASE = "https://sa2.esmplus.com"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _check_jwt(request):
    token = request.headers["Authorization"].split(" ", 1)[1]
    claims = pyjwt.decode(token, SECRET, algorithms=["HS256"], audience="sa.esmplus.com")
    assert claims["iss"] == "www.esmplus.com" and claims["sub"] == "sell" and claims["ssi"] == "A:iacseller,G:gmkseller"
    assert isinstance(claims["iat"], int)
    assert pyjwt.get_unverified_header(token)["kid"] == "master_1"


@pytest.mark.asyncio
@respx.mock
async def test_probe_sends_an_hs256_jwt_with_the_master_id_as_kid():
    route = respx.get(f"{BASE}/item/v1/shipping/delivery-company").mock(return_value=httpx.Response(200, json={"deliveryCompanies": [{"deliveryCompCode": 10013, "deliveryCompName": "CJ대한통운"}]}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["ok"] is True
    _check_jwt(route.calls[0].request)


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_posts_the_request_orders_body():
    route = respx.post(f"{BASE}/shipping/v1/Order/RequestOrders").mock(return_value=httpx.Response(200, json={"ResultCode": 0, "Message": "", "Data": {
        "TotalCount": 1, "RequestOrders": [{"OrderNo": 2946269058, "OrderStatus": 1, "AcntMoney": "25000", "PayDate": "2019-04-10T17:45:50.507", "NoSongjang": None}]}}))
    res = await _server().call_tool("list_orders", {"status": "paid", "since": "2026-09-01", "limit": 50})
    assert res.is_error is False
    o = res.structured_content["orders"][0]
    assert o["id"] == "2946269058" and o["total"] == "25000" and o["currency"] == "KRW" and res.structured_content["total"] == 1
    body = json.loads(route.calls[0].request.content)
    assert body["siteType"] == 2 and body["orderStatus"] == 1 and body["requestDateType"] == 2 and body["requestDateFrom"] == "2026-09-01"
    assert body["pageIndex"] == 1 and body["pageSize"] == 50 and len(body["requestDateTo"]) == 10
    _check_jwt(route.calls[0].request)


@pytest.mark.asyncio
@respx.mock
async def test_mark_shipped_and_result_code_error():
    route = respx.post(f"{BASE}/shipping/v1/Delivery/ShippingInfo").mock(side_effect=[
        httpx.Response(200, json={"ResultCode": 0, "Message": "Success", "Data": {"OrderNo": 2503423671}}),
        httpx.Response(200, json={"ResultCode": 3000, "Message": "해당 주문 내역이 없습니다.", "Data": None})])
    s = _server()
    ok = await s.call_tool("mark_shipped", {"order_id": "2503423671", "carrier": "10013", "tracking_number": "123456789012"})
    assert ok.is_error is False and ok.structured_content["status"] == "shipped"
    body = json.loads(route.calls[0].request.content)
    assert body["OrderNo"] == 2503423671 and body["DeliveryCompanyCode"] == 10013 and body["InvoiceNo"] == "123456789012"
    assert len(body["ShippingDate"]) == 19 and body["ShippingDate"][10] == "T"
    bad = await s.call_tool("mark_shipped", {"order_id": "1", "carrier": "10013", "tracking_number": "x"})
    assert bad.is_error is True


@pytest.mark.asyncio
@respx.mock
async def test_price_and_stock_go_to_both_sites():
    price = respx.put(f"{BASE}/item/v1/goods/4805864401/price").mock(return_value=httpx.Response(200, json={"resultCode": 0, "message": "[GMKT] 성공", "goodsNo": 4805864401}))
    stock = respx.put(f"{BASE}/item/v1/goods/4805864401/stock").mock(return_value=httpx.Response(200, json={"resultCode": 0, "message": "[IAC] 성공 / [GMKT] 성공", "goodsNo": 4805864401}))
    s = _server()
    r1 = await s.call_tool("update_listing", {"listing_id": "4805864401", "price": 12900})
    assert r1.is_error is False and r1.structured_content["status"] == "[GMKT] 성공"
    assert json.loads(price.calls[0].request.content) == {"gmkt": 12900, "iac": 12900}
    r2 = await s.call_tool("set_inventory", {"listing_id": "4805864401", "quantity": 7})
    assert r2.is_error is False
    assert json.loads(stock.calls[0].request.content) == {"stock": {"gmkt": 7, "iac": 7}}
