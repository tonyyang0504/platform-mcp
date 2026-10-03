import hashlib
import json
import sys
import time
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "temu.json").read_text(encoding="utf-8"))
CREDS = {"app_key": "f9d5cc9313893a20d5aa85c654e8f503", "app_secret": "c7e0a1a63542be4de3cb5488f9fba8149e8fc290", "access_token": "2nifvmpyymvypwmcms5ct4uqqudrwgpmzbcnmkt1jzjkuaf3x56iixym", "region": "us"}
ROUTER = "https://openapi-b-us.temu.com/openapi/router"


def _server(creds=None):
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(creds or CREDS), 50, "test", envelope=a.get("envelope")))


def _check_sign(request):
    body = json.loads(request.content)
    sig = body.pop("sign")
    parts = "".join(k + (v if isinstance(v, str) else json.dumps(v, separators=(",", ":"), ensure_ascii=False)) for k, v in sorted(body.items()))
    assert sig == hashlib.md5((CREDS["app_secret"] + parts + CREDS["app_secret"]).encode()).hexdigest().upper()
    assert body["app_key"] == CREDS["app_key"] and body["access_token"] == CREDS["access_token"] and body["data_type"] == "JSON"
    assert isinstance(body["timestamp"], int) and abs(body["timestamp"] - time.time()) < 60
    return body


def test_signature_matches_the_documented_example():
    # "Signature Method for API request", steps 2-4: the documented request must hash to 4CCF219942D4180C6DDA3CE36C1B838F
    send = [{"orderSendInfoList": [{"quantity": 1, "orderSn": "211-21905473070712792", "parentOrderSn": "PO-211-21905452099192792", "goodsId": 601099548666279, "skuId": 17592352673534}],
             "carrierId": "699272611", "trackingNumber": "270324232756"}]
    body = {"access_token": CREDS["access_token"], "app_key": CREDS["app_key"], "data_type": "JSON", "sendRequestList": send, "sendType": 0, "timestamp": 1711009072, "type": "bg.logistics.shipment.confirm"}
    parts = "".join(k + (v if isinstance(v, str) else json.dumps(v, separators=(",", ":"), ensure_ascii=False)) for k, v in sorted(body.items()))
    assert hashlib.md5((CREDS["app_secret"] + parts + CREDS["app_secret"]).encode()).hexdigest().upper() == "4CCF219942D4180C6DDA3CE36C1B838F"


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_signs_inside_the_json_body():
    route = respx.post(ROUTER).mock(return_value=httpx.Response(200, json={"success": True, "errorCode": 1000000, "result": {"totalItemNum": 1, "pageItems": [
        {"parentOrderMap": {"parentOrderSn": "PO-211-01", "parentOrderStatus": 2, "parentOrderTime": 1790000000}, "orderList": [{"orderSn": "211-01", "quantity": 1}]}]}}))
    res = await _server().call_tool("list_orders", {"status": "unshipped", "since": "2026-09-01", "limit": 50})
    assert res.is_error is False
    o = res.structured_content["orders"][0]
    assert o["id"] == "PO-211-01" and o["status"] == 2 and res.structured_content["total"] == 1
    body = _check_sign(route.calls[0].request)
    assert body["type"] == "bg.order.list.v2.get" and body["parentOrderStatus"] == 2 and body["pageSize"] == 50 and body["pageNumber"] == 1
    assert body["createAfter"] == 1788220800 and body["createBefore"] == 4102444800
    assert "sign" not in route.calls[0].request.url.params


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_without_since_sends_no_time_window():
    route = respx.post(ROUTER).mock(return_value=httpx.Response(200, json={"success": True, "result": {"totalItemNum": 0, "pageItems": []}}))
    assert (await _server().call_tool("list_orders", {})).is_error is False
    body = _check_sign(route.calls[0].request)
    assert "createAfter" not in body and "createBefore" not in body and "parentOrderStatus" not in body


@pytest.mark.asyncio
@respx.mock
async def test_set_inventory_and_eu_gateway():
    route = respx.post("https://openapi-b-eu.temu.com/openapi/router").mock(return_value=httpx.Response(200, json={"success": True, "result": {"goodsId": 601099548666279, "operateResult": True, "msg": "ok"}}))
    res = await _server({**CREDS, "region": "eu"}).call_tool("set_inventory", {"listing_id": "601099548666279", "sku": "17592352673534", "quantity": 12})
    assert res.is_error is False and res.structured_content["ok"] is True
    body = _check_sign(route.calls[0].request)
    assert body["goodsId"] == 601099548666279 and body["skuStockTargetList"] == [{"skuId": 17592352673534, "stockTarget": 12}]


@pytest.mark.asyncio
@respx.mock
async def test_failure_envelope_is_an_error_without_secrets():
    respx.post(ROUTER).mock(return_value=httpx.Response(200, json={"success": False, "errorCode": 3000032, "errorMsg": "access_token don't have this api access"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and CREDS["access_token"] not in json.dumps(res.structured_content)
