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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "alibaba_dropshipping.json").read_text(encoding="utf-8"))
CREDS = {"app_key": "500123", "app_secret": "ali-secret-0123456789", "access_token": "50000601c30atpedfgu3LVvik87Ixlsvle3mSoB", "ship_to_country": "US", "currency": "USD"}
REST = "https://openapi-api.alibaba.com/rest"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _check_sign(request, api_path):
    params = dict(parse_qsl(urlsplit(str(request.url)).query, keep_blank_values=True))
    sig = params.pop("sign")
    base = api_path + "".join(k + params[k] for k in sorted(params))
    assert sig == hmac.new(CREDS["app_secret"].encode(), base.encode(), hashlib.sha256).hexdigest().upper()
    assert params["app_key"] == "500123" and params["access_token"] == CREDS["access_token"] and len(params["timestamp"]) == 13
    return params


@pytest.mark.asyncio
@respx.mock
async def test_product_search_sends_param0_json():
    route = respx.get(url__startswith=f"{REST}/eco/buyer/product/search").mock(return_value=httpx.Response(200, json={"code": "0", "result": {"code": "200", "data": {
        "pagination": {"total_product_count": "2000"}, "products": [{"product_id": "1600398490", "title": "Wireless Bluetooth Earbuds", "price": "99", "permalink": "https://www.alibaba.com/product-detail/x.html", "image": {"main_image": "https://s01.alicdn.com/image01.jpg"}}]}}}))
    res = await _server().call_tool("list_products", {"query": "earbuds", "limit": 20, "page": 2})
    p = res.structured_content["products"][0]
    assert res.is_error is False and p["id"] == "1600398490" and p["image_url"] == "https://s01.alicdn.com/image01.jpg"
    params = _check_sign(route.calls[0].request, "/eco/buyer/product/search")
    assert json.loads(params["param0"]) == {"keyword": "earbuds", "index": 2, "size": 20, "shipToCountry": "US", "currency": "USD"}


@pytest.mark.asyncio
@respx.mock
async def test_freight_quote_and_order_create():
    q = respx.get(url__startswith=f"{REST}/shipping/freight/calculate").mock(return_value=httpx.Response(200, json={"code": "0", "value": [
        {"vendor_code": "EX_ASP_Economy_Express_3C", "vendor_name": "Alibaba.com Economy Express (3C)", "fee": {"amount": "19.1", "currency": "USD"}, "delivery_time": "10~15"}]}))
    o = respx.post(url__startswith=f"{REST}/buynow/order/create").mock(return_value=httpx.Response(200, json={"code": "0", "value": {"trade_id": "12345321", "pay_url": "https://pay.example/x"}}))
    s = _server()
    quote = await s.call_tool("quote_shipping", {"product_id": "213421", "country": "US", "quantity": 3})
    assert quote.is_error is False and quote.structured_content["options"][0]["code"] == "EX_ASP_Economy_Express_3C"
    qp = _check_sign(q.calls[0].request, "/shipping/freight/calculate")
    assert qp["product_id"] == "213421" and qp["destination_country"] == "US" and qp["quantity"] == "3"
    items = [{"product_id": 213421, "quantity": "3", "sku_id": "106117950042"}]
    addr = {"address": "Washington Square", "city": "New York", "country": "United States of America", "country_code": "US", "zip": "10012", "contact_person": "Ann Lee"}
    created = await s.call_tool("create_order", {"items": items, "shipping_address": addr, "shipping_option": "EX_ASP_Economy_Express_3C"})
    assert created.is_error is False and created.structured_content["id"] == "12345321" and created.structured_content["pay_url"] == "https://pay.example/x"
    op = _check_sign(o.calls[0].request, "/buynow/order/create")
    assert json.loads(op["product_list"]) == items
    assert json.loads(op["logistics_detail"]) == {"carrier_code": "EX_ASP_Economy_Express_3C", "shipment_address": addr}
    assert len(op["channel_refer_id"]) == 36


@pytest.mark.asyncio
@respx.mock
async def test_order_get_and_tracking():
    respx.get(url__startswith=f"{REST}/alibaba/order/get").mock(return_value=httpx.Response(200, json={"code": "0", "value": {"trade_id": "234193410001028893", "trade_status": "delivering",
        "total_amount": {"amount": "4.8700", "currency": "USD"}, "create_date": {"timestamp": "1733821832000"}}}))
    t = respx.get(url__startswith=f"{REST}/order/logistics/tracking/get").mock(return_value=httpx.Response(200, json={"code": "0", "tracking_list": [
        {"carrier": "FEDEX", "tracking_number": "776705370628", "current_event_code": "DELIVERED", "event_list": [{"event_name": "Delivered", "event_time": "2024-06-11 15:53:00"}]}]}))
    s = _server()
    o = await s.call_tool("get_order", {"id": "234193410001028893"})
    assert o.is_error is False and o.structured_content["status"] == "delivering" and o.structured_content["total"] == "4.8700"
    tr = await s.call_tool("track", {"order_id": "234193410001028893"})
    assert tr.is_error is False and tr.structured_content["events"][0]["tracking_number"] == "776705370628"
    assert _check_sign(t.calls[0].request, "/order/logistics/tracking/get")["trade_id"] == "234193410001028893"


@pytest.mark.asyncio
@respx.mock
async def test_error_code_is_an_error_result_without_secrets():
    respx.get(url__startswith=f"{REST}/alibaba/order/list").mock(return_value=httpx.Response(200, json={"type": "ISV", "code": "IllegalAccessToken", "message": "invalid token 50000601c30atpedfgu3LVvik87Ixlsvle3mSoB"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and CREDS["access_token"] not in json.dumps(res.structured_content)
