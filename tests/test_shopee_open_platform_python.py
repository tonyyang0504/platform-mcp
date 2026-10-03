import hashlib
import hmac
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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "shopee_open_platform.json").read_text(encoding="utf-8"))
CREDS = {"partner_id": "2001887", "partner_key": "shpk-partner-key-0123", "shop_id": "322300222", "refresh_token": "4c72595349-one", "host": "partner.shopeemobile.com"}
HOST = "https://partner.shopeemobile.com"
TOKEN_PATH = "/api/v2/auth/access_token/get"


def _server(creds=None):
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], {**a["auth"], "state_key": "shopee"}, creds if creds is not None else dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _hmac(s):
    return hmac.new(CREDS["partner_key"].encode(), s.encode(), hashlib.sha256).hexdigest()


def _token(access="71594a4c5453-A1", refresh="516c6b5777-two"):
    return respx.post(url__startswith=HOST + TOKEN_PATH).mock(return_value=httpx.Response(200, json={"error": "", "message": "", "partner_id": 2001887, "shop_id": 322300222, "access_token": access, "refresh_token": refresh, "expire_in": 14400}))


@pytest.mark.asyncio
@respx.mock
async def test_signed_refresh_then_signed_shop_call(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_MCP_STATE_DIR", str(tmp_path))
    tok = _token()
    me = respx.get(url__startswith=HOST + "/api/v2/shop/get_shop_info").mock(return_value=httpx.Response(200, json={"error": "", "shop_name": "openapi_pshop_1", "region": "SG"}))
    creds = dict(CREDS)
    res = await _server(creds).call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["shop_name"] == "openapi_pshop_1"
    t = tok.calls[0].request
    q = dict(t.url.params)
    assert q["partner_id"] == "2001887" and q["sign"] == _hmac("2001887" + TOKEN_PATH + q["timestamp"])
    assert json.loads(t.content) == {"refresh_token": "4c72595349-one", "partner_id": 2001887, "shop_id": 322300222}
    m = dict(me.calls[0].request.url.params)
    assert m["access_token"] == "71594a4c5453-A1" and m["shop_id"] == "322300222" and m["partner_id"] == "2001887"
    assert m["sign"] == _hmac("2001887" + "/api/v2/shop/get_shop_info" + m["timestamp"] + "71594a4c5453-A1" + "322300222")
    assert creds["refresh_token"] == "516c6b5777-two" and json.loads((tmp_path / "shopee.json").read_text())["refresh_token"] == "516c6b5777-two"


@pytest.mark.asyncio
@respx.mock
async def test_items_detail_order_and_tracking():
    _token()
    respx.get(url__startswith=HOST + "/api/v2/product/get_item_list").mock(return_value=httpx.Response(200, json={"error": "", "response": {"item": [{"item_id": 2500139861, "item_status": "NORMAL", "update_time": 1608128470}], "total_count": 1, "has_next_page": False}}))
    respx.get(url__startswith=HOST + "/api/v2/product/get_item_base_info").mock(return_value=httpx.Response(200, json={"error": "", "response": {"item_list": [{"item_id": 34002, "item_name": "Mug", "price_info": [{"currency": "SGD", "current_price": 12.5}]}]}}))
    respx.get(url__startswith=HOST + "/api/v2/order/get_order_detail").mock(return_value=httpx.Response(200, json={"error": "", "response": {"order_list": [{"order_sn": "201214JAJXU6G7", "order_status": "READY_TO_SHIP", "total_amount": 25.0, "currency": "SGD"}]}}))
    tr = respx.get(url__startswith=HOST + "/api/v2/logistics/get_tracking_info").mock(return_value=httpx.Response(200, json={"error": "", "response": {"order_sn": "201214JAJXU6G7", "logistics_status": "LOGISTICS_DELIVERY_DONE", "tracking_info": [{"update_time": 1726561500, "description": "Delivered"}]}}))
    s = _server()
    lst = await s.call_tool("list_products", {"page": 2, "limit": 10})
    assert lst.structured_content["products"][0]["id"] == "2500139861"
    g = await s.call_tool("get_product", {"id": "34002"})
    assert g.structured_content["title"] == "Mug" and g.structured_content["price"] == 12.5
    o = await s.call_tool("get_order", {"id": "201214JAJXU6G7"})
    assert o.structured_content["status"] == "READY_TO_SHIP"
    t = await s.call_tool("track", {"order_id": "201214JAJXU6G7"})
    assert t.structured_content["status"] == "LOGISTICS_DELIVERY_DONE" and t.structured_content["events"][0]["description"] == "Delivered"
    assert tr.calls[0].request.url.params["order_sn"] == "201214JAJXU6G7"


@pytest.mark.asyncio
@respx.mock
async def test_error_field_is_an_error_and_secrets_are_scrubbed():
    _token()
    respx.get(url__startswith=HOST + "/api/v2/order/get_order_detail").mock(return_value=httpx.Response(200, json={"error": "error_auth", "message": "Invalid access_token 71594a4c5453-A1"}))
    res = await _server().call_tool("get_order", {"id": "X"})
    assert res.is_error is True and "71594a4c5453-A1" not in json.dumps(res.structured_content) and CREDS["partner_key"] not in json.dumps(res.structured_content)
