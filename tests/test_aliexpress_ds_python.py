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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "aliexpress_ds.json").read_text(encoding="utf-8"))
CREDS = {"app_key": "500123", "app_secret": "ae-secret-0123456789", "access_token": "50000601c30atpedfgu3LVvik87", "ship_to_country": "US", "currency": "USD", "language": "en_US"}
SYNC = "https://api-sg.aliexpress.com/sync"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _check_sign(request):
    params = dict(parse_qsl(urlsplit(str(request.url)).query, keep_blank_values=True))
    sig = params.pop("sign")
    base = "".join(k + params[k] for k in sorted(params))
    assert sig == hmac.new(b"ae-secret-0123456789", base.encode(), hashlib.sha256).hexdigest().upper()
    return params


@pytest.mark.asyncio
@respx.mock
async def test_text_search_is_signed_over_sorted_parameters():
    route = respx.get(SYNC).mock(return_value=httpx.Response(200, json={"code": "0", "aliexpress_ds_text_search_response": {"code": "0", "data": {
        "totalCount": 120, "products": [{"itemId": "1005005511268056", "title": "Car sunshade", "targetSalePrice": "6.62", "targetOriginalPriceCurrency": "USD",
                                           "itemUrl": "https://www.aliexpress.com/item/1005005511268056.html", "itemMainPic": "https://ae01.alicdn.com/x.jpg"}]}}, "request_id": "r1"}))
    res = await _server().call_tool("list_products", {"query": "sunshade", "limit": 20, "page": 2})
    assert res.is_error is False
    p = res.structured_content["products"][0]
    assert p["id"] == "1005005511268056" and p["price"] == "6.62" and p["currency"] == "USD"
    assert res.structured_content["total"] == 120
    params = _check_sign(route.calls.last.request)
    assert params["method"] == "aliexpress.ds.text.search" and params["keyWord"] == "sunshade"
    assert params["pageIndex"] == "2" and params["pageSize"] == "20" and params["countryCode"] == "US" and params["local"] == "en_US"
    assert params["app_key"] == "500123" and params["access_token"] == CREDS["access_token"] and params["sign_method"] == "sha256"
    assert params["timestamp"].isdigit() and len(params["timestamp"]) == 13


@pytest.mark.asyncio
@respx.mock
async def test_create_order_sends_the_place_order_dto_as_one_json_parameter():
    route = respx.post(SYNC).mock(return_value=httpx.Response(200, json={"code": "0", "aliexpress_ds_order_create_response": {"result": {"is_success": "true", "order_list": [8190001234]}}}))
    items = [{"product_id": "1005005511268056", "product_count": 2, "sku_attr": "14:175#Black", "logistics_service_name": "CAINIAO_STANDARD"}]
    addr = {"address": "1 Main St", "city": "Austin", "province": "Texas", "country": "US", "zip": "78701", "full_name": "Ann Lee", "mobile_no": "5125550100", "phone_country": "+1"}
    res = await _server().call_tool("create_order", {"items": items, "shipping_address": addr})
    assert res.is_error is False and res.structured_content["id"] == "8190001234"
    params = _check_sign(route.calls.last.request)
    assert params["method"] == "aliexpress.ds.order.create"
    assert json.loads(params["param_place_order_request4_open_api_d_t_o"]) == {"logistics_address": addr, "product_items": items}


@pytest.mark.asyncio
@respx.mock
async def test_get_order_and_track():
    def handler(request):
        q = dict(parse_qsl(urlsplit(str(request.url)).query))
        if q["method"] == "aliexpress.trade.ds.order.get":
            assert json.loads(q["single_order_query"]) == {"order_id": 8190001234}
            return httpx.Response(200, json={"aliexpress_trade_ds_order_get_response": {"result": {"order_status": "WAIT_BUYER_ACCEPT_GOODS", "gmt_create": "2026-09-20 05:39:01",
                                             "order_amount": {"amount": "13.24", "currency_code": "USD"}, "logistics_info_list": [{"logistics_no": "LP00123", "logistics_service": "CAINIAO_STANDARD"}]}}})
        assert q["ae_order_id"] == "8190001234" and q["language"] == "en_US"
        return httpx.Response(200, json={"code": "0", "aliexpress_ds_order_tracking_get_response": {"result": {"ret": "true", "data": {"tracking_detail_line_list": [
            {"mail_no": "LP00123", "carrier_name": "AliExpress Standard Shipping", "detail_node_list": [{"time_stamp": "1720181940000", "tracking_detail_desc": "Package delivered"}]}]}}}})
    respx.get(SYNC).mock(side_effect=handler)
    s = _server()
    o = await s.call_tool("get_order", {"id": "8190001234"})
    assert o.structured_content["status"] == "WAIT_BUYER_ACCEPT_GOODS" and o.structured_content["tracking_number"] == "LP00123" and o.structured_content["total"] == "13.24"
    t = await s.call_tool("track", {"order_id": "8190001234"})
    ev = t.structured_content["events"][0]
    assert ev["tracking_number"] == "LP00123" and ev["latest"] == "Package delivered"


@pytest.mark.asyncio
@respx.mock
async def test_illegal_access_token_is_an_auth_error_without_secrets():
    respx.get(SYNC).mock(return_value=httpx.Response(200, json={"code": "IllegalAccessToken", "type": "ISV", "message": "The specified access token is invalid or expired: 50000601c30atpedfgu3LVvik87", "request_id": "r2"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert CREDS["access_token"] not in json.dumps(res.structured_content)
