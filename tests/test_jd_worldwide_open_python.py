import hashlib
import json
import sys
import time as _time
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "jd_worldwide_open.json").read_text(encoding="utf-8"))
CREDS = {"app_key": "123456780233FA31AD94AA59CFA65305", "app_secret": "jd-secret-0123456789", "access_token": "12345678-b0e1-4d0c-9d10-a998d9597d75"}
ROUTER = "https://api.jd.com/routerjson"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _check_sign(request):
    params = dict(parse_qsl(urlsplit(str(request.url)).query, keep_blank_values=True))
    sig = params.pop("sign")
    base = "".join(k + params[k] for k in sorted(params))
    assert sig == hashlib.md5((CREDS["app_secret"] + base + CREDS["app_secret"]).encode()).hexdigest().upper()
    assert params["app_key"] == CREDS["app_key"] and params["access_token"] == CREDS["access_token"] and params["v"] == "2.0"
    return params


@pytest.mark.asyncio
@respx.mock
async def test_timestamp_is_beijing_time_and_the_call_is_signed(monkeypatch):
    monkeypatch.setattr(_time, "time", lambda: 1790301600.0)  # 2026-09-25 02:00:00 UTC → 10:00:00 in Beijing
    route = respx.get(url__startswith=ROUTER).mock(return_value=httpx.Response(200, json={"jingdong_seller_vender_info_get_responce": {"vender_info_result": {"vender_id": "10001", "shop_name": "xx专卖店"}}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False
    params = _check_sign(route.calls[0].request)
    assert params["timestamp"] == "2026-09-25 10:00:00" and params["method"] == "jingdong.seller.vender.info.get" and params["360buy_param_json"] == "{}"


@pytest.mark.asyncio
@respx.mock
async def test_ware_search_sends_360buy_param_json():
    route = respx.get(url__startswith=ROUTER).mock(return_value=httpx.Response(200, json={"jingdong_ware_read_searchWare4Valid_responce": {"page": {"totalItem": 200, "data": [
        {"wareId": "5319765", "title": "iphone15手机", "jdPrice": "5999.00", "stockNum": "500", "itemNum": "31231241", "logo": "jfs/t1/x.jpg"}]}}}))
    res = await _server().call_tool("list_products", {"query": "手机", "limit": 30, "page": 2})
    assert res.is_error is False
    p = res.structured_content["products"][0]
    assert p["id"] == "5319765" and p["price"] == "5999.00" and p["currency"] == "CNY" and res.structured_content["total"] == 200
    params = _check_sign(route.calls[0].request)
    body = json.loads(params["360buy_param_json"])
    assert params["method"] == "jingdong.ware.read.searchWare4Valid"
    assert body["searchKey"] == "手机" and body["pageNo"] == 2 and body["pageSize"] == 30 and body["searchField"] == "title"


@pytest.mark.asyncio
@respx.mock
async def test_get_order_maps_order_info():
    route = respx.get(url__startswith=ROUTER).mock(return_value=httpx.Response(200, json={"jingdong_pop_order_get_responce": {"orderDetailInfo": {"apiResult": {"success": "true"}, "orderInfo": {
        "orderId": "67834311", "orderState": "WAIT_SELLER_STOCK_OUT", "orderPayment": "90", "orderStartTime": "2019-01-01 12:21:32", "waybill": "SF534221"}}}}))
    res = await _server().call_tool("get_order", {"id": "67834311"})
    sc = res.structured_content
    assert res.is_error is False and sc["id"] == "67834311" and sc["status"] == "WAIT_SELLER_STOCK_OUT" and sc["tracking_number"] == "SF534221"
    params = _check_sign(route.calls[0].request)
    assert json.loads(params["360buy_param_json"])["order_id"] == 67834311


@pytest.mark.asyncio
@respx.mock
async def test_gateway_error_response_is_an_error_without_secrets():
    respx.get(url__startswith=ROUTER).mock(return_value=httpx.Response(200, json={"error_response": {"code": "19", "zh_desc": "token已过期或者不存在，请重新授权访问 12345678-b0e1-4d0c-9d10-a998d9597d75", "en_desc": "Invalid access_token"}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and CREDS["access_token"] not in json.dumps(res.structured_content, ensure_ascii=False)
