import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "marketplaces" / "taobao.json").read_text(encoding="utf-8"))
CREDS = {"app_key": "12345678", "app_secret": "tb-secret-abcdef", "session": "6100a1b2c3d4e5session"}
GW = "https://gw.api.taobao.com/router/rest"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _check(request):
    q = dict(parse_qsl(urlsplit(str(request.url)).query, keep_blank_values=True))
    sig = q.pop("sign")
    assert sig == hashlib.md5((CREDS["app_secret"] + "".join(k + q[k] for k in sorted(q)) + CREDS["app_secret"]).encode()).hexdigest().upper()
    assert q["app_key"] == "12345678" and q["session"] == CREDS["session"] and q["v"] == "2.0" and q["sign_method"] == "md5" and q["format"] == "json"
    assert CREDS["app_secret"] not in str(request.url)
    return q


@pytest.mark.asyncio
@respx.mock
async def test_timestamp_is_gmt8_and_the_md5_signature_matches(monkeypatch):
    import time as _t
    monkeypatch.setattr(_t, "time", lambda: 1790301600.0)
    route = respx.get(url__startswith=GW).mock(return_value=httpx.Response(200, json={"user_seller_get_response": {"user": {"user_id": 10001, "nick": "hz0799", "type": "C"}}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False
    q = _check(route.calls[0].request)
    assert q["timestamp"] == "2026-09-25 10:00:00"  # 02:00 UTC = 10:00 GMT+8
    assert q["method"] == "taobao.user.seller.get"


@pytest.mark.asyncio
@respx.mock
async def test_items_onsale_are_listed():
    route = respx.get(url__startswith=GW).mock(return_value=httpx.Response(200, json={"items_onsale_get_response": {"total_results": 150, "items": {"item": [
        {"num_iid": 1489161932, "title": "Google test item", "price": "5.00", "approve_status": "onsale", "list_time": "2009-10-22 14:22:06"}]}}}))
    res = await _server().call_tool("list_products", {"page": 2, "limit": 40})
    p = res.structured_content["products"][0]
    assert p["id"] == "1489161932" and p["price"] == "5.00" and p["currency"] == "CNY" and res.structured_content["total"] == 150
    q = _check(route.calls[0].request)
    assert q["method"] == "taobao.items.onsale.get" and q["page_no"] == "2" and q["page_size"] == "40" and "num_iid" in q["fields"]


@pytest.mark.asyncio
@respx.mock
async def test_trades_and_refunds_since():
    def handler(request):
        q = dict(parse_qsl(urlsplit(str(request.url)).query))
        if q["method"] == "taobao.trades.sold.get":
            assert q["start_created"] == "2026-09-01 00:00:00"
            return httpx.Response(200, json={"trades_sold_get_response": {"total_results": 1, "trades": {"trade": [{"tid": 2231884277, "status": "WAIT_SELLER_SEND_GOODS", "payment": "200.07", "created": "2026-09-20 12:00:00",
                                                                                                                 "orders": {"order": [{"num_iid": 1489161932, "title": "Google test item"}]}}]}}})
        assert q["method"] == "taobao.refunds.receive.get" and q["start_modified"] == "2026-09-01 00:00:00"
        return httpx.Response(200, json={"refunds_receive_get_response": {"total_results": 1, "refunds": {"refund": [{"refund_id": "83477", "tid": 2231884277, "refund_fee": "10.00", "status": "WAIT_SELLER_AGREE"}]}}})
    respx.get(url__startswith=GW).mock(side_effect=handler)
    s = _server()
    sales = await s.call_tool("list_sales", {"since": "2026-09-01"})
    sale = sales.structured_content["sales"][0]
    assert sale["id"] == "2231884277" and sale["product_id"] == "1489161932" and sale["amount"] == "200.07"
    refunds = await s.call_tool("list_refunds", {"since": "2026-09-01"})
    assert refunds.structured_content["refunds"][0]["sale_id"] == "2231884277"


@pytest.mark.asyncio
@respx.mock
async def test_error_response_is_an_is_error():
    respx.get(url__startswith=GW).mock(return_value=httpx.Response(200, json={"error_response": {"code": 27, "msg": "Invalid session", "sub_code": "invalid-sessionkey", "request_id": "x"}}))
    res = await _server().call_tool("get_product", {"product_id": "1"})
    assert res.is_error is True and CREDS["session"] not in json.dumps(res.structured_content)
