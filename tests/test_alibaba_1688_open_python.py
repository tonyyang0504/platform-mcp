import hashlib
import hmac
import json
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "alibaba_1688_open.json").read_text(encoding="utf-8"))
CREDS = {"client_id": "1000000", "client_secret": "test123", "refresh_token": "479f9564-1049-456e-ab62-29d3e82277d9", "language": "en", "order_flow": "saleproxy"}
GW = "https://gw.open.1688.com"
TOKEN = f"{GW}/openapi/http/1/system.oauth2/getToken/1000000"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _token():
    return respx.post(TOKEN).mock(return_value=httpx.Response(200, json={"aliId": "8888888888", "expires_in": "36000", "access_token": "f14da3b8-b0b1-4f73-a5de-9bed637e0188"}))


def _check_sign(request):
    params = dict(parse_qsl(urlsplit(str(request.url)).query, keep_blank_values=True))
    sig = params.pop("_aop_signature")
    url_path = request.url.path[len("/openapi/"):]
    s = url_path + "".join(k + params[k] for k in sorted(params))
    assert sig == hmac.new(b"test123", s.encode(), hashlib.sha1).hexdigest().upper()
    assert params["access_token"] == "f14da3b8-b0b1-4f73-a5de-9bed637e0188"
    return params


def test_documented_signature_example():
    # https://open.1688.com/doc/signature.htm: param2/1/system/currentTime/1000000 with b=2&a=1, secret test123
    assert hmac.new(b"test123", b"param2/1/system/currentTime/1000000a1b2", hashlib.sha1).hexdigest().upper() == "33E54F4F7B989E3E0E912D3FBD2F1A03CA7CCE88"


@pytest.mark.asyncio
@respx.mock
async def test_refresh_then_signed_probe():
    tok = _token()
    me = respx.get(url__startswith=f"{GW}/openapi/param2/1/system/currentTime/1000000").mock(return_value=httpx.Response(200, json={"result": "20260925101010000+0800"}))
    assert (await _server().call_tool("me", {})).is_error is False
    assert dict(parse_qsl(tok.calls[0].request.content.decode())) == {"grant_type": "refresh_token", "refresh_token": CREDS["refresh_token"], "client_id": "1000000", "client_secret": "test123"}
    params = _check_sign(me.calls[0].request)
    assert params["_aop_timestamp"].isdigit()


@pytest.mark.asyncio
@respx.mock
async def test_keyword_search_and_detail():
    _token()
    search = respx.post(url__startswith=f"{GW}/openapi/param2/1/com.alibaba.fenxiao.crossborder/product.search.keywordQuery/1000000").mock(return_value=httpx.Response(200, json={"result": {"success": True, "code": "200", "result": {
        "totalRecords": 123, "data": [{"offerId": 620201390233, "subject": "饼干", "subjectTrans": "Biscuits", "imageUrl": "https://cbu01.alicdn.com/x.jpg", "priceInfo": {"price": "10", "consignPrice": "12"}}]}}}))
    detail = respx.post(url__startswith=f"{GW}/openapi/param2/1/com.alibaba.fenxiao.crossborder/product.search.queryProductDetail/1000000").mock(return_value=httpx.Response(200, json={"result": {"success": True, "result": {
        "offerId": 620201390233, "subjectTrans": "Biscuits", "productImage": {"images": ["https://cbu01.alicdn.com/a.jpg"]}, "productSkuInfos": [{"specId": "b266e0726506185beaf205cbae88530d", "price": "9.5"}], "productSaleInfo": {"amountOnSale": 99999}}}}))
    s = _server()
    lst = await s.call_tool("list_products", {"query": "biscuits", "limit": 10, "page": 2})
    p = lst.structured_content["products"][0]
    assert lst.is_error is False and p["id"] == "620201390233" and p["title"] == "Biscuits" and p["price"] == "10" and lst.structured_content["total"] == 123
    q = _check_sign(search.calls[0].request)
    assert json.loads(q["offerQueryParam"]) == {"keyword": "biscuits", "beginPage": 2, "pageSize": 10, "country": "en"}
    one = await s.call_tool("get_product", {"id": "620201390233"})
    assert one.is_error is False and one.structured_content["sku"] == "b266e0726506185beaf205cbae88530d" and one.structured_content["stock"] == 99999
    assert json.loads(_check_sign(detail.calls[0].request)["offerDetailParam"]) == {"offerId": 620201390233, "country": "en"}


@pytest.mark.asyncio
@respx.mock
async def test_fast_create_order_and_gateway_error():
    _token()
    route = respx.post(url__startswith=f"{GW}/openapi/param2/1/com.alibaba.trade/alibaba.trade.fastCreateOrder/1000000").mock(side_effect=[
        httpx.Response(200, json={"success": True, "result": {"orderId": "58218860983545941", "totalSuccessAmount": 6150}}),
        httpx.Response(200, json={"error_code": "gw.QosAppFrequencyLimit", "error_message": "App call exceeds limited frequency"})])
    s = _server()
    items = [{"offerId": 554456348334, "specId": "b266e0726506185beaf205cbae88530d", "quantity": 5}]
    addr = {"fullName": "张三", "mobile": "15251667788", "provinceText": "浙江省", "cityText": "杭州市", "areaText": "滨江区", "address": "网商路699号", "postCode": "000000"}
    ok = await s.call_tool("create_order", {"items": items, "shipping_address": addr})
    assert ok.is_error is False and ok.structured_content["id"] == "58218860983545941"
    p = _check_sign(route.calls[0].request)
    assert p["flow"] == "saleproxy" and json.loads(p["cargoParamList"]) == items and json.loads(p["addressParam"]) == addr
    bad = await s.call_tool("create_order", {"items": items, "shipping_address": addr})
    assert bad.is_error is True


@pytest.mark.asyncio
@respx.mock
async def test_order_and_trace():
    _token()
    respx.post(url__startswith=f"{GW}/openapi/param2/1/com.alibaba.trade/alibaba.trade.get.buyerView/1000000").mock(return_value=httpx.Response(200, json={"success": "true", "result": {"baseInfo": {
        "idOfStr": "58218860983545941", "status": "waitbuyerreceive", "totalAmount": 6.15, "createTime": "20170913231708000-0700"}}}))
    tr = respx.post(url__startswith=f"{GW}/openapi/param2/1/com.alibaba.logistics/alibaba.trade.getLogisticsTraceInfo.buyerView/1000000").mock(return_value=httpx.Response(200, json={"logisticsTrace": [
        {"logisticsId": "LP00106397027178", "logisticsBillNo": "3832890717253", "logisticsSteps": [{"acceptTime": "2018-07-24 21:55:33", "remark": "揽件扫描"}]}]}))
    s = _server()
    o = await s.call_tool("get_order", {"id": "58218860983545941"})
    assert o.is_error is False and o.structured_content["status"] == "waitbuyerreceive" and o.structured_content["total"] == 6.15
    t = await s.call_tool("track", {"order_id": "58218860983545941"})
    assert t.is_error is False and t.structured_content["events"][0]["tracking_number"] == "3832890717253"
    p = _check_sign(tr.calls[0].request)
    assert p["webSite"] == "1688" and p["orderId"] == "58218860983545941"
