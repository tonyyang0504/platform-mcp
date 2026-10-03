import hashlib
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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "temu_seller.json").read_text(encoding="utf-8"))
CREDS = {"app_key": "f9d5cc9313893a20d5aa85c654e8f503", "app_secret": "c7e0a1a63542be4de3cb5488f9fba8149e8fc290", "access_token": "2nifvmpyymvypwmcms5ct4uq", "region": "us"}
URL = "https://openapi-b-us.temu.com/openapi/router"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _check(request):
    body = json.loads(request.content)
    sig = body.pop("sign")
    kv = "".join(k + (v if isinstance(v, str) else json.dumps(v, separators=(",", ":"), ensure_ascii=False)) for k, v in sorted(body.items()))
    assert sig == hashlib.md5((CREDS["app_secret"] + kv + CREDS["app_secret"]).encode()).hexdigest().upper()
    assert body["app_key"] == CREDS["app_key"] and body["access_token"] == CREDS["access_token"] and body["data_type"] == "JSON"
    assert isinstance(body["timestamp"], int) and CREDS["app_secret"] not in request.content.decode()
    return body


@pytest.mark.asyncio
@respx.mock
async def test_goods_list_is_signed_inside_the_body():
    route = respx.post(URL).mock(return_value=httpx.Response(200, json={"success": True, "errorCode": 1000000, "result": {"total": 3, "goodsList": [
        {"goodsId": 601099548666279, "goodsName": "Desk lamp", "retailPrice": {"amount": "19.99", "currency": "USD"}, "outGoodsSn": "LAMP-1", "quantity": 12}]}}))
    res = await _server().call_tool("list_products", {"query": "lamp", "category": "12345", "page": 1, "limit": 20})
    p = res.structured_content["products"][0]
    assert p["id"] == "601099548666279" and p["price"] == "19.99" and p["currency"] == "USD" and res.structured_content["total"] == 3
    body = _check(route.calls[0].request)
    assert body["type"] == "bg.local.goods.list.query" and body["pageNo"] == 1 and body["pageSize"] == 20
    assert body["searchText"] == "lamp" and body["catIdList"] == [12345] and body["goodsSearchType"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_goods_detail_and_order_detail():
    def handler(request):
        b = _check(request)
        if b["type"] == "bg.local.goods.detail.query":
            assert b["goodsId"] == 601099548666279
            return httpx.Response(200, json={"success": True, "result": {"goodsId": 601099548666279, "goodsName": "Desk lamp", "skuList": [{"outSkuSn": "LAMP-1-W", "retailPrice": {"amount": "19.99", "currency": "USD"}}]}})
        assert b["type"] == "bg.order.detail.v2.get" and b["parentOrderSn"] == "PO-211-21905452099192792"
        return httpx.Response(200, json={"success": True, "result": {"parentOrderMap": {"parentOrderSn": "PO-211-21905452099192792", "parentOrderStatus": 2, "parentOrderTime": 1788000000}, "orderList": []}})
    respx.post(URL).mock(side_effect=handler)
    s = _server()
    g = await s.call_tool("get_product", {"id": "601099548666279"})
    assert g.structured_content["sku"] == "LAMP-1-W"
    o = await s.call_tool("get_order", {"id": "PO-211-21905452099192792"})
    assert o.structured_content["id"] == "PO-211-21905452099192792" and o.structured_content["status"] == 2


@pytest.mark.asyncio
@respx.mock
async def test_success_false_is_an_error():
    respx.post(URL).mock(return_value=httpx.Response(200, json={"success": False, "errorCode": 7000015, "errorMsg": "sign is invalid"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and "sign is invalid" in json.dumps(res.structured_content)
