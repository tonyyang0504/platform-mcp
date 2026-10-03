import base64
import hashlib
import hmac
import json
import sys
import time as _time
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "shein.json").read_text(encoding="utf-8"))
# the documented example (Signature Rules): OpenKeyId, decrypted SecretKey, RandomKey "test1"
CREDS = {"open_key_id": "B96C15416C9240DF96BAA0BC9B367C6D", "sign_key": "6BEC9C4B668B4B14B17EEF106BB98AE5test1", "random_key": "test1",
         "site": "shein-us", "currency": "USD", "warehouse_code": "PS0426919682"}
API = "https://openapi.sheincorp.com"


def _server(spec=SPEC):
    a = spec["adapter"]
    return build_server(spec, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _check_sign(request):
    h = request.headers
    value = f"{CREDS['open_key_id']}&{h['x-lt-timestamp']}&{request.url.path}"
    hexsig = hmac.new(CREDS["sign_key"].encode(), value.encode(), hashlib.sha256).hexdigest()
    assert h["x-lt-signature"] == "test1" + base64.b64encode(hexsig.encode()).decode()
    assert h["x-lt-openKeyId"] == CREDS["open_key_id"] and h["language"] == "en"


@pytest.mark.asyncio
@respx.mock
async def test_runtime_reproduces_the_documented_signature(monkeypatch):
    monkeypatch.setattr(_time, "time", lambda: 1740709414.0)
    spec = json.loads(json.dumps(SPEC))
    spec["adapter"]["tools"]["me"]["path"] = "/open-api/order/purchase-order-info"
    route = respx.get(f"{API}/open-api/order/purchase-order-info").mock(return_value=httpx.Response(200, json={"code": "0", "msg": "OK", "info": {}}))
    assert (await _server(spec).call_tool("me", {})).is_error is False
    h = route.calls[0].request.headers
    assert h["x-lt-timestamp"] == "1740709414000"
    assert h["x-lt-signature"] == "test1ZDZjYTJjNzg5ZjUzMDdkZTU2N2Y3NzcxN2ZjZjA5OGIxMTRhZWI0MTU1MzQxNjZlNjFkMGQxOTJiYTk1YWNjYQ=="


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_for_one_beijing_day():
    route = respx.post(f"{API}/open-api/order/order-list").mock(return_value=httpx.Response(200, json={"code": "0", "msg": "OK", "info": {"count": 2, "orderList": [
        {"orderNo": "GSON8H44Y0004CU", "orderStatus": "1", "orderCreateTime": "2023-08-09 18:03:04"}]}}))
    res = await _server().call_tool("list_orders", {"since": "2026-09-24", "status": "2", "limit": 30})
    assert res.is_error is False and res.structured_content["orders"][0]["id"] == "GSON8H44Y0004CU"
    body = json.loads(route.calls[0].request.content)
    assert body == {"queryType": 1, "startTime": "2026-09-24 00:00:00", "endTime": "2026-09-24 23:59:00", "page": 1, "pageSize": 30, "orderStatus": 2, "queryOrderType": 4}
    _check_sign(route.calls[0].request)


@pytest.mark.asyncio
@respx.mock
async def test_stock_price_and_delist_bodies():
    stock = respx.post(f"{API}/open-api/stock/change-inventory/v2").mock(return_value=httpx.Response(200, json={"code": "0", "msg": "OK", "info": {"failedList": []}}))
    price = respx.post(f"{API}/open-api/openapi-business-backend/product/price/save").mock(return_value=httpx.Response(200, json={"code": "0", "info": {"data": [{"success": True, "status": 1}]}}))
    shelf = respx.post(f"{API}/open-api/goods/modify-skc-shelf").mock(return_value=httpx.Response(200, json={"code": "0", "msg": "OK", "info": {"success_count": 1, "failure_count": 0}}))
    s = _server()
    assert (await s.call_tool("set_inventory", {"sku": "I11mesukkwwr", "quantity": 7})).is_error is False
    req = json.loads(stock.calls[0].request.content)["updateSkuInventoryQuantityRequests"][0]
    assert req["skuCode"] == "I11mesukkwwr" and req["changeQuantity"] == 7 and req["changeType"] == "OVERWRITE" and req["invType"] == "VI" and req["warehouseCode"] == "PS0426919682" and len(req["idempotencyKey"]) == 36
    await s.call_tool("update_listing", {"listing_id": "I11mesukkwwr", "price": 19.99})
    assert json.loads(price.calls[0].request.content) == {"productPriceList": [{"productCode": "I11mesukkwwr", "currencyCode": "USD", "shopPrice": 19.99, "site": "shein-us"}]}
    off = await s.call_tool("end_listing", {"listing_id": "sMM23072039123259"})
    assert off.is_error is False and off.structured_content["failures"] == 0
    assert json.loads(shelf.calls[0].request.content) == {"skc_site_info_list": [{"shelf_state": 2, "site_list": ["shein-us"], "skc_name": "sMM23072039123259"}]}
    _check_sign(shelf.calls[0].request)


@pytest.mark.asyncio
@respx.mock
async def test_error_code_is_an_error_result():
    respx.get(f"{API}/open-api/msc/warehouse/list").mock(return_value=httpx.Response(200, json={"code": "10010", "msg": "signature error"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and CREDS["sign_key"] not in json.dumps(res.structured_content)
