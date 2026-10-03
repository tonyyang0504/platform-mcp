import hashlib
import hmac
import json
import sys
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "douyin_ecommerce.json").read_text(encoding="utf-8"))
CREDS = {"app_key": "6844048284663924231", "app_secret": "749698a6-fcb3-4358-b241-ec1d93cf9c1f", "access_token": "c6f957da-1239-4343-84a1-c84e68915ff7"}
BASE = "https://openapi-fxg.jinritemai.com"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _expected_sign(q: dict) -> str:
    signed = {k: v for k, v in q.items() if k not in ("sign", "access_token", "sign_method")}
    s = CREDS["app_secret"] + "".join(k + signed[k] for k in sorted(signed)) + CREDS["app_secret"]
    return hmac.new(CREDS["app_secret"].encode(), s.encode(), hashlib.sha256).hexdigest()


@pytest.mark.asyncio
@respx.mock
async def test_signature_excludes_access_token_and_uses_gmt8_timestamp(monkeypatch):
    monkeypatch.setattr(time, "time", lambda: 1790301600.0)  # 2026-09-25 02:00:00 UTC = 10:00:00 GMT+8
    route = respx.get(url__startswith=BASE + "/product/listV2").mock(return_value=httpx.Response(200, json={"code": 10000, "msg": "success", "data": {
        "data": [{"product_id": 3600137140018749665, "name": "测试商品", "img": "https://p3.example/a.jpg", "status": 0, "check_status": 3}], "total": 41, "page": 2, "size": 20}}))
    res = await _server().call_tool("list_products", {"page": 2, "limit": 20})
    assert res.is_error is False
    p = res.structured_content["products"][0]
    assert p["id"] == "3600137140018749665" and p["title"] == "测试商品" and res.structured_content["total"] == 41
    q = dict(parse_qsl(urlsplit(str(route.calls[0].request.url)).query))
    assert q["method"] == "product.listV2" and q["param_json"] == '{"page":"2","size":"20"}'
    assert q["timestamp"] == "2026-09-25 10:00:00" and q["v"] == "2" and q["app_key"] == CREDS["app_key"]
    assert q["access_token"] == CREDS["access_token"] and q["sign_method"] == "hmac-sha256"
    assert q["sign"] == _expected_sign(q)


@pytest.mark.asyncio
@respx.mock
async def test_product_detail_and_order_detail():
    respx.get(url__startswith=BASE + "/product/detail").mock(return_value=httpx.Response(200, json={"code": 10000, "data": {"product_id_str": "3600137140018749665", "name": "测试商品", "discount_price": 1990, "img": "x"}}))
    order = respx.get(url__startswith=BASE + "/order/orderDetail").mock(return_value=httpx.Response(200, json={"code": 10000, "data": {"shop_order_detail": {
        "order_id": "6496679971677798670", "order_status": 3, "order_status_desc": "已发货", "pay_amount": 5990, "create_time": 1790300000,
        "logistics_info": [{"tracking_no": "SF1234567890", "company_name": "顺丰速运", "ship_time": 1790301000}]}}}))
    s = _server()
    g = await s.call_tool("get_product", {"id": "3600137140018749665"})
    assert g.structured_content["id"] == "3600137140018749665" and g.structured_content["price"] == 1990
    t = await s.call_tool("track", {"order_id": "6496679971677798670"})
    assert t.structured_content["tracking_number"] == "SF1234567890" and t.structured_content["carrier"] == "顺丰速运"
    q = dict(parse_qsl(urlsplit(str(order.calls[0].request.url)).query))
    assert q["param_json"] == '{"shop_order_id":"6496679971677798670"}' and q["sign"] == _expected_sign(q)


@pytest.mark.asyncio
@respx.mock
async def test_non_10000_code_is_an_error():
    respx.get(url__startswith=BASE + "/order/orderDetail").mock(return_value=httpx.Response(200, json={"code": 40004, "msg": "非法的参数", "sub_code": "isv.parameter-invalid", "sub_msg": "订单不存在"}))
    res = await _server().call_tool("get_order", {"id": "1"})
    assert res.is_error is True and "非法的参数" in res.structured_content["message"]
