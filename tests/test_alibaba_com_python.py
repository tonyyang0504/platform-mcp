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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "alibaba_com.json").read_text(encoding="utf-8"))
CREDS = {"app_key": "12345678", "app_secret": "helloworld", "access_token": "50000601c30atpedfgu3LVvik87Ixlsvle3mSoB7701ceb156fPunYZ43GBg"}
REST = "https://openapi-api.alibaba.com/rest"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _check_sign(request, api_path):
    params = dict(parse_qsl(urlsplit(str(request.url)).query, keep_blank_values=True))
    sig = params.pop("sign")
    assert sig == hmac.new(b"helloworld", (api_path + "".join(k + params[k] for k in sorted(params))).encode(), hashlib.sha256).hexdigest().upper()
    assert params["sign_method"] == "sha256" and params["app_key"] == "12345678" and params["access_token"] == CREDS["access_token"]
    return params


def test_documented_signature_example():
    # docId=61 step 5: /auth/token/create with App Secret "helloworld"
    base = "/auth/token/createapp_key12345678code3_500102_JxZ05Ux3cnnSSUm6dCxYg6Q26sign_methodsha256simplifytruetimestamp1517820392000"
    assert hmac.new(b"helloworld", base.encode(), hashlib.sha256).hexdigest().upper() == "0B409A354C6FB222EE2C8095002ACDB2D30566151D1A2361AEE7D2627B9BCBEA"


@pytest.mark.asyncio
@respx.mock
async def test_seller_order_list_signs_the_path_without_rest():
    route = respx.get(url__startswith=f"{REST}/alibaba/order/list").mock(return_value=httpx.Response(200, json={"code": "0", "value": {"total_count": "1", "order_list": [
        {"trade_id": "271207727001028893", "trade_status": "undeliver", "create_date": {"timestamp": "1754021376000"}}]}}))
    res = await _server().call_tool("list_orders", {"status": "undeliver", "since": "2026-09-01", "limit": 10, "page": 2})
    assert res.is_error is False and res.structured_content["orders"][0]["id"] == "271207727001028893"
    params = _check_sign(route.calls[0].request, "/alibaba/order/list")
    assert params["role"] == "seller" and params["start_page"] == "1" and params["page_size"] == "10" and params["status"] == "undeliver"
    assert json.loads(params["create_date_start"]) == {"date_timestamp": 1788220800000}


@pytest.mark.asyncio
@respx.mock
async def test_price_inventory_and_offline():
    def handler(request):
        return httpx.Response(200, json={"code": "0", "result": {"success": True}, "success": True})
    route = respx.post(url__startswith=REST).mock(side_effect=handler)
    s = _server()
    assert (await s.call_tool("update_listing", {"listing_id": "1601314875038", "price": 12.5})).is_error is False
    p = _check_sign(route.calls[0].request, "/icbu/product/edit-price")
    assert p["product_id"] == "1601314875038" and json.loads(p["price"]) == {"price_type": "TIERED", "tiered_price": [{"quantity": 1, "price": "12.5"}], "currency": "USD"}
    assert (await s.call_tool("set_inventory", {"listing_id": "1601314875038", "quantity": 40})).is_error is False
    assert _check_sign(route.calls[1].request, "/icbu/product/edit-inventory")["inventory"] == "40"
    off = await s.call_tool("end_listing", {"listing_id": "1601314875038"})
    assert off.is_error is False and off.structured_content["status"] == "offline"
    p3 = _check_sign(route.calls[2].request, "/alibaba/icbu/product/batch/update/status")
    assert json.loads(p3["product_id_list"]) == [1601314875038] and p3["action"] == "offline"


@pytest.mark.asyncio
@respx.mock
async def test_illegal_access_token_is_an_auth_error():
    respx.get(url__startswith=f"{REST}/alibaba/order/list").mock(return_value=httpx.Response(200, json={"type": "ISV", "code": "IllegalAccessToken", "message": "The specified access token is invalid or expired"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
