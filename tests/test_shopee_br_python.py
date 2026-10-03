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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "shopee_br.json").read_text(encoding="utf-8"))
CREDS = {"partner_id": "1001", "shop_id": "600000", "partner_key": "PKEY-shopee-0123456789", "refresh_token": "REFRESH-sp-1"}
HOST = "https://openplatform.shopee.com.br"


def _server(creds=None):
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(creds or CREDS), 50, "test", envelope=a.get("envelope")))


def _token(new_refresh="REFRESH-sp-2"):
    return respx.post(url__startswith=f"{HOST}/api/v2/auth/access_token/get").mock(return_value=httpx.Response(200, json={
        "error": "", "message": "", "access_token": "ACCESS-sp", "refresh_token": new_refresh, "expire_in": 14400, "request_id": "r"}))


def _mac(s):
    return hmac.new(CREDS["partner_key"].encode(), s.encode(), hashlib.sha256).hexdigest()


@pytest.mark.asyncio
@respx.mock
async def test_signed_refresh_then_signed_shop_call(monkeypatch):
    monkeypatch.setattr(_time, "time", lambda: 1790301600.0)
    tok = _token()
    me = respx.get(url__startswith=f"{HOST}/api/v2/shop/get_shop_info").mock(return_value=httpx.Response(200, json={"error": "", "message": "", "shop_name": "My Shop", "region": "SG", "status": "NORMAL"}))
    assert (await _server().call_tool("me", {})).is_error is False
    t = tok.calls[0].request
    assert json.loads(t.content) == {"refresh_token": "REFRESH-sp-1", "partner_id": 1001, "shop_id": 600000}
    assert t.url.params["partner_id"] == "1001" and t.url.params["timestamp"] == "1790301600"
    assert t.url.params["sign"] == _mac("1001/api/v2/auth/access_token/get1790301600")
    q = me.calls[0].request.url.params
    assert q["access_token"] == "ACCESS-sp" and q["shop_id"] == "600000" and q["partner_id"] == "1001"
    assert q["sign"] == _mac("1001/api/v2/shop/get_shop_info1790301600ACCESS-sp600000")
    assert "Authorization" not in me.calls[0].request.headers


@pytest.mark.asyncio
@respx.mock
async def test_order_list_cursor_and_rotation_persisted(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_MCP_STATE_DIR", str(tmp_path))
    _token("REFRESH-sp-rotated")
    route = respx.get(url__startswith=f"{HOST}/api/v2/order/get_order_list").mock(return_value=httpx.Response(200, json={"error": "", "message": "", "response": {
        "more": True, "next_cursor": "20", "order_list": [{"order_sn": "201218V2Y6E59M", "order_status": "READY_TO_SHIP"}]}}))
    res = await _server().call_tool("list_orders", {"since": "2026-09-20", "status": "READY_TO_SHIP", "limit": 20})
    sc = res.structured_content
    assert res.is_error is False and sc["orders"][0]["id"] == "201218V2Y6E59M" and sc["next_cursor"] == "20"
    q = route.calls[0].request.url.params
    assert q["time_range_field"] == "create_time" and q["time_from"] == "1789862400" and int(q["time_to"]) > 1789862400 and q["order_status"] == "READY_TO_SHIP" and q["page_size"] == "20"
    assert json.loads((tmp_path / "shopee_br.json").read_text())["refresh_token"] == "REFRESH-sp-rotated"


@pytest.mark.asyncio
@respx.mock
async def test_stock_price_unlist_and_ship_bodies():
    _token()
    def ok(request):
        return httpx.Response(200, json={"error": "", "message": "", "response": {"failure_list": [], "success_list": []}})
    route = respx.post(url__startswith=f"{HOST}/api/v2/").mock(side_effect=ok)
    s = _server()
    assert (await s.call_tool("set_inventory", {"listing_id": "1000", "sku": "0", "quantity": 25})).is_error is False
    assert (await s.call_tool("update_listing", {"listing_id": "1000", "price": 11.11})).is_error is False
    assert (await s.call_tool("end_listing", {"listing_id": "2300069665"})).is_error is False
    assert (await s.call_tool("mark_shipped", {"order_id": "201212DCXHJUIKJ", "tracking_number": "TRK123"})).is_error is False
    bodies = [json.loads(c.request.content) for c in route.calls if "access_token/get" not in c.request.url.path]
    assert bodies[0] == {"item_id": 1000, "stock_list": [{"model_id": 0, "seller_stock": [{"stock": 25}]}]}
    assert bodies[1] == {"item_id": 1000, "price_list": [{"model_id": 0, "original_price": 11.11}]}
    assert bodies[2] == {"item_list": [{"item_id": 2300069665, "unlist": True}]}
    assert bodies[3] == {"order_sn": "201212DCXHJUIKJ", "non_integrated": {"tracking_number": "TRK123"}}


@pytest.mark.asyncio
@respx.mock
async def test_error_field_is_an_error_result():
    _token()
    respx.get(url__startswith=f"{HOST}/api/v2/shop/get_shop_info").mock(return_value=httpx.Response(200, json={"error": "error_auth", "message": "Invalid access_token.", "request_id": "r"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and "ACCESS-sp" not in json.dumps(res.structured_content)
